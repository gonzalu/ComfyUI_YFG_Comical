"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Pick a specific or truly-random image from a directory (optionally recursive), with session-level de-duplication and optional random.org.
"""

import os
import re
import json
import time
import hashlib
import random
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

import folder_paths
import node_helpers
import requests

# ---------------- helpers ----------------

ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")

def natural_key(s: str):
    """Natural sort key that avoids comparing ints vs strs."""
    parts = re.findall(r'\d+|\D+', s)
    key = []
    for t in parts:
        if t.isdigit():
            key.append((0, int(t)))
        else:
            key.append((1, t.lower()))
    return key

def list_images(base_dir: str, include_subdirs: bool) -> List[Path]:
    base = Path(base_dir)
    if not base.exists():
        return []
    if include_subdirs:
        files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED_EXT]
    else:
        files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXT]
    # human-friendly sort by filename
    files.sort(key=lambda p: natural_key(p.name))
    return files

def pillow_to_tensor(img: Image.Image) -> torch.Tensor:
    output_images = []
    w = h = None
    for i in ImageSequence.Iterator(img):
        i = node_helpers.pillow(ImageOps.exif_transpose, i)
        if i.mode == "I":
            i = i.point(lambda x: x * (1 / 255))
        frame = i.convert("RGB")
        if not output_images:
            w, h = frame.size
        if frame.size != (w, h):
            raise ValueError("Image size mismatch across frames")
        arr = np.array(frame).astype(np.float32) / 255.0
        output_images.append(torch.from_numpy(arr)[None, ...])
    return output_images[0] if len(output_images) == 1 else torch.cat(output_images, dim=0)

def image_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

# ---- optional Random.org support ----

def _load_random_org_key() -> Optional[str]:
    # 1) env var
    ev = os.environ.get("RANDOM_ORG_API_KEY", "").strip()
    if ev:
        return ev
    # 2) json file next to this node file
    fp = Path(__file__).with_name("random_org_api_key.json")
    if fp.exists():
        try:
            return json.loads(fp.read_text())["api_key"].strip()
        except Exception:
            pass
    return None

def random_org_int(minimum: int, maximum: int) -> Optional[int]:
    api_key = _load_random_org_key()
    if not api_key:
        return None
    payload = {
        "jsonrpc":"2.0",
        "method":"generateIntegers",
        "params":{"apiKey":api_key,"n":1,"min":int(minimum),"max":int(maximum),"replacement":True,"base":10},
        "id":1
    }
    try:
        r = requests.post(
            "https://api.random.org/json-rpc/2/invoke",
            headers={"Content-Type":"application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return int(data["result"]["random"]["data"][0])
    except Exception:
        pass
    return None

# ---- session uniqueness ----

class _UniqueHistory:
    buckets = {}  # scope_key -> {seen:{value:(value,ts)}, order:[value,...]}

    @classmethod
    def _bucket(cls, scope_key: str):
        if scope_key not in cls.buckets:
            cls.buckets[scope_key] = {"seen": {}, "order": []}
        return cls.buckets[scope_key]

    @classmethod
    def remember_and_check(cls, scope_key: str, value_key: str, history_size: int, time_window_sec: int) -> bool:
        """
        Returns True if value_key was seen recently (within constraints).
        Records the current sighting regardless.
        """
        now = time.time()
        b = cls._bucket(scope_key)
        seen = b["seen"]
        order = b["order"]

        # prune by time
        if time_window_sec and time_window_sec > 0:
            cutoff = now - time_window_sec
            to_remove = [k for k, (_, ts) in seen.items() if ts < cutoff]
            for k in to_remove:
                seen.pop(k, None)
                try:
                    order.remove(k)
                except ValueError:
                    pass

        already = value_key in seen

        seen[value_key] = (value_key, now)
        order.append(value_key)

        # prune by size
        if history_size and history_size > 0:
            while len(order) > history_size:
                old = order.pop(0)
                seen.pop(old, None)

        return already

# ---------------- the node (original class name) ----------------

class RandomImageFromDirectory:
    """
    Select specific or random image from a directory/subdirs.
    Supports Random.org (optional) and session de-duplication.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_directory": ("STRING", {"multiline": False, "placeholder": "Image Directory"}),
                "include_subdirs": ("BOOLEAN", {"default": True}),
                # defaults changed here:
                "selection_mode": (["by_index", "by_filename", "by_query", "random"], {"default": "random"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "filename_query": ("STRING", {"multiline": False, "placeholder": "Exact filename or substring (by_filename/by_query)"}),
                # default changed here:
                "random_source": (["auto", "local", "random_org"], {"default": "auto"}),
                "ensure_unique": ("BOOLEAN", {"default": False}),
                "unique_scope": (["directory", "global"],),
                "history_size": ("INT", {"default": 512, "min": 1, "max": 100000}),
                "time_window_sec": ("INT", {"default": 0, "min": 0, "max": 604800}),
                "retry_limit": ("INT", {"default": 16, "min": 1, "max": 999}),
            }
        }


    # keep the first four outputs identical for backward compatibility,
    # then add current index & filename, then metadata


    RETURN_TYPES = (
        "IMAGE",
        "STRING",  # path_current
        "INT",     # index_current
        "STRING",  # filename_current
        "INT",     # width
        "INT",     # height
        "STRING",  # sha256
        "INT",     # total_count
        "STRING",  # path_previous
        "INT"      # index_previous
    )

    RETURN_NAMES = (
        "image",
        "path_current",
        "index_current",
        "filename_current",
        "width",
        "height",
        "sha256",
        "total_count",
        "path_previous",
        "index_previous"
    )

    FUNCTION = "load"
    CATEGORY = "🐯 YFG/🖼️ Loaders"

    _prev_index = -1
    _prev_path = ""

    def _pick_random_index(self, n: int, src: str, min_idx: int, max_idx: int) -> int:
        if n <= 0:
            return 0
        if src == "random_org" or (src == "auto" and _load_random_org_key()):
            v = random_org_int(min_idx, max_idx)
            if v is not None:
                return v
        return random.randint(min_idx, max_idx)

    def _choose(
        self,
        files: List[Path],
        selection_mode: str,
        index: int,
        filename_query: str,
        rand_src: str,
        ensure_unique: bool,
        unique_scope: str,
        history_size: int,
        time_window_sec: int,
        retry_limit: int,
        directory: str
    ) -> Tuple[Optional[Path], int]:
        n = len(files)
        if n == 0:
            return None, -1

        def try_accept(idx: int) -> Optional[Path]:
            p = files[idx]
            if ensure_unique:
                scope_key = "global" if unique_scope == "global" else f"dir::{Path(directory).resolve()}"
                val_key = str(p.resolve())
                if _UniqueHistory.remember_and_check(scope_key, val_key, history_size, time_window_sec):
                    return None
            return p

        if selection_mode == "by_index":
            idx = index % n
            p = try_accept(idx)
            if p is None and ensure_unique:
                for _ in range(retry_limit):
                    idx = (idx + 1) % n
                    p = try_accept(idx)
                    if p is not None:
                        break
            return p, idx

        if selection_mode == "by_filename":
            q = filename_query.strip()
            if not q:
                return None, -1
            # exact first
            exact = [i for i, p in enumerate(files) if p.name == q]
            cand = exact if exact else [i for i, p in enumerate(files) if q.lower() in p.name.lower()]
            if not cand:
                return None, -1
            idx = cand[0]
            p = try_accept(idx) or files[idx]
            return p, idx

        if selection_mode == "by_query":
            q = filename_query.strip() or "*"
            regex = re.compile("^" + re.escape(q).replace(r"\*", ".*").replace(r"\?", ".") + "$", re.IGNORECASE)
            cand = [i for i, p in enumerate(files) if regex.match(p.name)]
            if not cand:
                return None, -1
            tries = 0
            while tries < max(1, retry_limit):
                pick = cand[self._pick_random_index(len(cand)-1, rand_src, 0, len(cand)-1)]
                p = try_accept(pick)
                if p is not None or not ensure_unique:
                    return (p or files[pick]), pick
                tries += 1
            return files[pick], pick  # fall back

        # random
        tries = 0
        idx = self._pick_random_index(n-1, rand_src, 0, n-1)
        while tries < max(1, retry_limit):
            p = try_accept(idx)
            if p is not None or not ensure_unique:
                return (p or files[idx]), idx
            idx = (idx + 1) % n
            tries += 1
        return files[idx], idx  # last resort


    def load(
        self,
        image_directory,
        include_subdirs,
        selection_mode,
        index,
        filename_query,
        random_source,
        ensure_unique,
        unique_scope,
        history_size,
        time_window_sec,
        retry_limit
    ):
        if not os.path.exists(image_directory):
            raise Exception(f"Image directory {image_directory} does not exist")

        files = list_images(image_directory, include_subdirs)
        if not files:
            raise Exception(f"No images found in '{image_directory}' (include_subdirs={include_subdirs})")

        total_count = len(files)
    
        path, idx = self._choose(
            files, selection_mode, index, filename_query, random_source,
            ensure_unique, unique_scope, history_size, time_window_sec,
            retry_limit, image_directory
        )
        if path is None:
            raise Exception("Could not select an image with the given parameters (possibly all candidates were recently used).")

        img = node_helpers.pillow(Image.open, str(path))
        img_tensor = pillow_to_tensor(img)

        # backward-compatible first 4
        filename_path = str(path)
        prev_index = RandomImageFromDirectory._prev_index
        prev_path = RandomImageFromDirectory._prev_path

        # update session prev
        RandomImageFromDirectory._prev_index = idx
        RandomImageFromDirectory._prev_path = filename_path

        w, h = img.size
        sha = image_sha256(path)

        # then add current index/filename + metadata
        
        return (
            img_tensor,
            filename_path,        # path_current
            int(idx),             # index_current
            path.name,            # filename_current
            int(w),
            int(h),
            sha,
            int(total_count),     # total_count
            prev_path,            # path_previous
            prev_index            # index_previous
        )

    @classmethod
    def IS_CHANGED(cls, image_directory, include_subdirs, selection_mode, index, filename_query,
                   random_source, ensure_unique, unique_scope, history_size, time_window_sec,
                   retry_limit, **kwargs):
        # If randomness or de-duplication can change the output between runs,
        # force recomputation every time.
        if selection_mode in ("random", "by_query") or ensure_unique or random_source in ("auto", "random_org"):
            return float("NaN")

        # Otherwise, stable hash allows caching for deterministic selections.
        m = hashlib.sha256()
        for v in (image_directory, include_subdirs, selection_mode, index, filename_query,
                  random_source, ensure_unique, unique_scope, history_size, time_window_sec, retry_limit):
            m.update(str(v).encode("utf-8"))
            m.update(b"|")
        return m.hexdigest()

