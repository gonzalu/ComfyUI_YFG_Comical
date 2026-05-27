"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Selects a random prompt from a .txt prompt file using true random.org
              numbers. Single self-contained node with file browser, history cache,
              and multiple selection modes.

Changelog:
  1.1.0  Simplified inputs: removed first_n/last_n/custom_range/n_pool.
         range_start/range_end auto-populate from file when selected in UI.
         Added last_n_only toggle + last_n_count to restrict pool to newest entries.
  1.0.0  Initial release.
"""

from __future__ import annotations

import os
import re
import json
import time
import hashlib
import random
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NODE_VERSION = "1.1.0"

# ─────────────────────────── file format ──────────────────────────────────────
# Prompt file format:
#   positive: text
#   negative: text   (required field, may be empty)
#   name: text       (optional, defaults to filename stem)
# Entries separated by one or more hyphens on their own line (any length).
# Leading/trailing separator lines are silently ignored.

_SEPARATOR_RE = re.compile(r'\n\s*-+\s*\n')
_PROMPT_RE    = re.compile(
    r"^(?:(?:positive:(?P<positive>.*?)|negative:(?P<negative>.*?)|name:(?P<name>.*?))\n*)+$",
    re.DOTALL | re.IGNORECASE,
)

# ─────────────────────────── prompt file cache ────────────────────────────────

class _PromptFileCache:
    """Parses and caches prompt files. Re-parses only when file mtime changes."""
    _cache: Dict[str, dict] = {}

    @classmethod
    def load(cls, filepath: str) -> List[Tuple[str, str, str]]:
        try:
            mtime = os.path.getmtime(filepath)
        except OSError:
            return []
        cached = cls._cache.get(filepath)
        if cached and cached["mtime"] == mtime:
            return cached["prompts"]
        prompts = cls._parse(filepath)
        cls._cache[filepath] = {"mtime": mtime, "prompts": prompts}
        print(f"[YFG] RandomPromptFromFile: parsed {len(prompts)} prompts from '{Path(filepath).name}'")
        return prompts

    @classmethod
    def _parse(cls, filepath: str) -> List[Tuple[str, str, str]]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            print(f"[YFG] RandomPromptFromFile: cannot read '{filepath}': {e}")
            return []
        blocks  = _SEPARATOR_RE.split(data)
        prompts = []
        stem    = Path(filepath).stem
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            m = _PROMPT_RE.search(block)
            if m:
                positive = (m.group("positive") or "").strip()
                negative = (m.group("negative") or "").strip()
                name     = (m.group("name")     or "").strip() or stem
                prompts.append((positive, negative, name))
            else:
                print(f"[YFG] RandomPromptFromFile: skipping unrecognized block in '{Path(filepath).name}'")
        return prompts


# ─────────────────────────── file history ─────────────────────────────────────

_FILE_HISTORY_PATH = Path(__file__).parent / "yfg_file_history.json"
_MAX_FILE_HISTORY  = 20


class _FileHistory:
    @classmethod
    def _read(cls) -> list:
        try:
            if _FILE_HISTORY_PATH.exists():
                data = json.loads(_FILE_HISTORY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(d) for d in data if isinstance(d, str) and d.strip()]
        except Exception:
            pass
        return []

    @classmethod
    def get(cls) -> list:
        return cls._read()

    @classmethod
    def add(cls, filepath: str):
        try:
            resolved = str(Path(filepath).resolve())
            files    = cls._read()
            if resolved in files:
                files.remove(resolved)
            files.insert(0, resolved)
            files = files[:_MAX_FILE_HISTORY]
            _FILE_HISTORY_PATH.write_text(json.dumps(files, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[YFG] FileHistory.add error: {e}")

    @classmethod
    def remove(cls, filepath: str):
        try:
            resolved = str(Path(filepath).resolve())
            files    = cls._read()
            if resolved in files:
                files.remove(resolved)
            _FILE_HISTORY_PATH.write_text(json.dumps(files, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[YFG] FileHistory.remove error: {e}")

    @classmethod
    def clear(cls):
        try:
            _FILE_HISTORY_PATH.write_text("[]", encoding="utf-8")
        except Exception as e:
            print(f"[YFG] FileHistory.clear error: {e}")


# ─────────────────────────── shuffle bag ──────────────────────────────────────

class _ShuffleBag:
    MAX_BAG_SIZE = 200_000
    _bags: Dict[str, dict] = {}

    @classmethod
    def can_use(cls, lo: int, hi: int) -> bool:
        return 1 <= (hi - lo + 1) <= cls.MAX_BAG_SIZE

    @classmethod
    def _get_bag(cls, key: str) -> dict:
        if key not in cls._bags:
            cls._bags[key] = {"remaining": [], "last_lo": None, "last_hi": None}
        return cls._bags[key]

    @classmethod
    def next_value(cls, bag_key: str, lo: int, hi: int) -> int:
        bag = cls._get_bag(bag_key)
        if bag["last_lo"] != lo or bag["last_hi"] != hi or not bag["remaining"]:
            values = list(range(lo, hi + 1))
            random.SystemRandom().shuffle(values)
            bag["remaining"] = values
            bag["last_lo"]   = lo
            bag["last_hi"]   = hi
        return int(bag["remaining"].pop(0))


# ─────────────────────────── uniqueness history ────────────────────────────────

class _UniqueHistory:
    _caches: Dict[str, dict] = {}

    @classmethod
    def _cache(cls, key: str) -> dict:
        if key not in cls._caches:
            cls._caches[key] = {"map": {}, "order": []}
        return cls._caches[key]

    @classmethod
    def is_duplicate(cls, value: int, scope: str, history_size: int, time_window: int) -> bool:
        now = time.time()
        c   = cls._cache(scope)
        cls._prune(c, history_size, time_window)
        ts  = c["map"].get(value)
        if ts is None:
            return False
        if time_window > 0 and (now - ts) > time_window:
            return False
        return True

    @classmethod
    def remember(cls, value: int, scope: str, history_size: int):
        c = cls._cache(scope)
        c["map"][value] = time.time()
        c["order"].append(value)
        cls._prune(c, history_size, 0)

    @classmethod
    def _prune(cls, c: dict, history_size: int, time_window: int):
        while len(c["order"]) > history_size:
            old = c["order"].pop(0)
            c["map"].pop(old, None)
        if time_window > 0:
            now = time.time()
            for v in list(c["order"]):
                ts = c["map"].get(v)
                if ts and (now - ts) > time_window:
                    c["order"].remove(v)
                    c["map"].pop(v, None)


# ─────────────────────────── API routes ───────────────────────────────────────

try:
    from server import PromptServer
    from aiohttp import web as _aio_web

    @PromptServer.instance.routes.get("/yfg/file_history")
    async def _yfg_get_file_history(request):
        return _aio_web.json_response(_FileHistory.get())

    @PromptServer.instance.routes.post("/yfg/file_history/add")
    async def _yfg_add_file_history(request):
        data     = await request.json()
        filepath = data.get("filepath", "").strip()
        if filepath:
            _FileHistory.add(filepath)
        return _aio_web.json_response({"ok": True, "history": _FileHistory.get()})

    @PromptServer.instance.routes.post("/yfg/file_history/remove")
    async def _yfg_remove_file_history(request):
        data     = await request.json()
        filepath = data.get("filepath", "").strip()
        if filepath:
            _FileHistory.remove(filepath)
        return _aio_web.json_response({"ok": True, "history": _FileHistory.get()})

    @PromptServer.instance.routes.post("/yfg/file_history/clear")
    async def _yfg_clear_file_history(request):
        _FileHistory.clear()
        return _aio_web.json_response({"ok": True})

    @PromptServer.instance.routes.get("/yfg/file_browse")
    async def _yfg_browse_files(request):
        """Navigator that returns both subdirectories and .txt files."""
        path        = request.query.get("path", "").strip()
        show_hidden = request.query.get("show_hidden", "false").lower() == "true"
        try:
            if not path:
                if platform.system() == "Windows":
                    import string
                    from ctypes import windll
                    drives, bitmask = [], windll.kernel32.GetLogicalDrives()
                    for letter in string.ascii_uppercase:
                        if bitmask & 1:
                            drives.append({"name": f"{letter}:\\", "path": f"{letter}:\\", "type": "dir"})
                        bitmask >>= 1
                    return _aio_web.json_response({
                        "path": "", "parent": None, "name": "Drives",
                        "entries": drives, "is_root": True,
                    })
                else:
                    candidates = ["/", str(Path.home()), "/mnt", "/media", "/Volumes", "/data"]
                    roots = [{"name": c, "path": c, "type": "dir"} for c in candidates if Path(c).exists()]
                    return _aio_web.json_response({
                        "path": "", "parent": None, "name": "Filesystem",
                        "entries": roots, "is_root": True,
                    })

            p = Path(path)
            if not p.exists() or not p.is_dir():
                return _aio_web.json_response({"error": f"Not a valid directory: {path}"}, status=400)

            dirs, files = [], []
            try:
                for item in sorted(p.iterdir(), key=lambda x: x.name.lower()):
                    if not show_hidden and item.name.startswith("."):
                        continue
                    if item.is_dir():
                        dirs.append({"name": item.name, "path": str(item), "type": "dir"})
                    elif item.is_file() and item.suffix.lower() == ".txt":
                        files.append({"name": item.name, "path": str(item), "type": "file"})
            except PermissionError:
                pass

            parent = str(p.parent) if str(p.parent) != str(p) else None
            return _aio_web.json_response({
                "path":    str(p),
                "parent":  parent,
                "name":    p.name or str(p),
                "entries": dirs + files,
                "is_root": False,
            })
        except Exception as e:
            return _aio_web.json_response({"error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/yfg/prompt_count")
    async def _yfg_prompt_count(request):
        """Returns total valid prompt count for a file (uses parse cache)."""
        filepath = request.query.get("path", "").strip()
        if not filepath or not Path(filepath).exists():
            return _aio_web.json_response({"count": 0, "error": "File not found"})
        prompts = _PromptFileCache.load(filepath)
        return _aio_web.json_response({"count": len(prompts)})

    print("[YFG] RandomPromptFromFile: API routes registered "
          "(/yfg/file_history, /yfg/file_browse, /yfg/prompt_count)")

except Exception as _api_err:
    print(f"[YFG] RandomPromptFromFile: Could not register API routes — {_api_err}")


# ─────────────────────────── random.org helpers ───────────────────────────────

def _load_api_key() -> Optional[str]:
    ev = os.environ.get("RANDOM_ORG_API_KEY", "").strip()
    if ev:
        return ev
    fp = Path(__file__).with_name("random_org_api_key.json")
    if fp.exists():
        try:
            return json.loads(fp.read_text())["api_key"].strip()
        except Exception:
            pass
    return None


def _random_org_int(api_key: str, lo: int, hi: int) -> Optional[int]:
    try:
        import requests
        payload = {
            "jsonrpc": "2.0", "method": "generateIntegers",
            "params": {"apiKey": api_key, "n": 1, "min": lo, "max": hi,
                       "replacement": True, "base": 10},
            "id": 1,
        }
        r = requests.post(
            "https://api.random.org/json-rpc/2/invoke",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload), timeout=10,
        )
        if r.status_code == 200:
            return int(r.json()["result"]["random"]["data"][0])
    except Exception:
        pass
    return None


def _rand_int(lo: int, hi: int, source: str) -> int:
    if source == "local":
        return random.randint(lo, hi)
    api_key = _load_api_key()
    if api_key and source in ("random_org", "auto"):
        result = _random_org_int(api_key, lo, hi)
        if result is not None:
            return result
    return random.randint(lo, hi)


# ─────────────────────────── main node ────────────────────────────────────────

class YFGRandomPromptFromFile:
    """
    YFG Random Prompt From File

    Selects a random prompt from a .txt prompt file using true random.org numbers.
    Single self-contained node — no additional nodes required.

    range_start / range_end auto-populate when a file is selected in the UI.
    last_n_only toggle restricts the pool to the last N entries in the file
    (useful when you append new prompts to the bottom and want fresh picks).
    """

    DESCRIPTION = (
        f"YFG Random Prompt From File (v{NODE_VERSION})\n\n"
        "Selects a random prompt from a .txt prompt file.\n\n"
        "File format:\n"
        "  positive: your positive prompt\n"
        "  negative: your negative prompt  (empty is fine)\n"
        "  name: optional label            (defaults to filename)\n"
        "  ----  (any number of hyphens as separator)\n\n"
        "range_start / range_end auto-fill when a file is selected.\n"
        "Toggle last_n_only to restrict picks to the newest entries.\n"
        "INDEX auto-syncs after every run — switch to by_index with no typing.\n"
    )

    OUTPUT_TOOLTIPS = (
        "Positive prompt text.",
        "Negative prompt text (empty if not in file).",
        "Prompt name — from 'name:' field or filename if omitted.",
        "0-based index of the selected prompt. Auto-syncs to INDEX widget.",
        "Index of the previously selected prompt this session.",
        "Total number of valid prompts found in the file.",
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_file": ("STRING", {
                    "multiline":   False,
                    "placeholder": "Path to .txt prompt file — use 📄 Browse or 🕐 Recent",
                    "tooltip":     "Full path to a .txt prompt file.",
                }),
                "selection_mode": (["random", "by_index"], {
                    "default": "random",
                    "tooltip": "random picks from range_start..range_end. by_index uses INDEX directly.",
                }),
                "index": ("INT", {
                    "default": 0,
                    "min":     0,
                    "max":     0xFFFFFFFFFFFFFFFF,
                    "tooltip": "Used by by_index mode. Auto-syncs after every run.",
                }),
                "range_start": ("INT", {
                    "default": 0,
                    "min":     0,
                    "max":     0xFFFFFFFFFFFFFFFF,
                    "tooltip": "First prompt index to include in random pool (auto-fills to 0 when file selected).",
                }),
                "range_end": ("INT", {
                    "default": 0,
                    "min":     0,
                    "max":     0xFFFFFFFFFFFFFFFF,
                    "tooltip": "Last prompt index to include in random pool (auto-fills to total-1 when file selected). 0 = last prompt.",
                }),
                "last_n_only": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "When ON, restricts the random pool to the last N entries only (newest prompts).",
                }),
                "last_n_count": ("INT", {
                    "default": 100,
                    "min":     1,
                    "max":     0xFFFFFFFFFFFFFFFF,
                    "tooltip": "How many entries from the end of the file to pick from (only active when last_n_only is ON).",
                }),
                "random_source": (["auto", "local", "random_org"], {
                    "default": "auto",
                    "tooltip": "auto uses random.org if API key exists; else local PRNG.",
                }),
                "ensure_unique": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Avoid repeating prompts within history_size / time_window_sec.",
                }),
                "history_size": ("INT", {
                    "default": 100,
                    "min":     1,
                    "max":     100000,
                    "tooltip": "How many recent indices to track for uniqueness.",
                }),
                "time_window_sec": ("INT", {
                    "default": 0,
                    "min":     0,
                    "max":     86400,
                    "tooltip": "If >0, forget uniqueness entries older than this many seconds.",
                }),
                "retry_limit": ("INT", {
                    "default": 20,
                    "min":     1,
                    "max":     1000,
                }),
                "use_shuffle_bag": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Cycle through all prompts before repeating, then reshuffle.",
                }),
            }
        }

    RETURN_TYPES  = ("STRING", "STRING", "STRING", "INT", "INT", "INT")
    RETURN_NAMES  = ("positive", "negative", "name",
                     "index_current", "index_previous", "total_count")
    FUNCTION      = "load_prompt"
    CATEGORY      = "🐯 YFG/📝 Prompts"

    def __init__(self):
        self._prev_index: int = -1

    def load_prompt(
        self,
        prompt_file:     str,
        selection_mode:  str,
        index:           int,
        range_start:     int,
        range_end:       int,
        last_n_only:     bool,
        last_n_count:    int,
        random_source:   str,
        ensure_unique:   bool,
        history_size:    int,
        time_window_sec: int,
        retry_limit:     int,
        use_shuffle_bag: bool,
    ):
        if not prompt_file or not os.path.isfile(prompt_file):
            raise Exception(
                f"[YFG] RandomPromptFromFile: file not found: '{prompt_file}'"
            )

        prompts = _PromptFileCache.load(prompt_file)
        if not prompts:
            raise Exception(
                f"[YFG] RandomPromptFromFile: no valid prompts found in '{prompt_file}'"
            )

        total    = len(prompts)
        prev_idx = self._prev_index

        if selection_mode == "by_index":
            idx = max(0, min(int(index), total - 1))
        else:
            # Resolve range
            lo = max(0, min(int(range_start), total - 1))
            hi = int(range_end) if int(range_end) > 0 else total - 1
            hi = max(lo, min(hi, total - 1))

            # last_n_only overrides lo to restrict pool to newest entries
            if last_n_only:
                lo = max(lo, hi - int(last_n_count) + 1)

            scope = f"file::{Path(prompt_file).resolve()}"
            idx   = self._pick(
                lo, hi, scope, random_source, ensure_unique,
                history_size, time_window_sec, retry_limit, use_shuffle_bag,
            )

        positive, negative, name = prompts[idx]
        self._prev_index = idx
        _FileHistory.add(prompt_file)

        print(
            f"[YFG] RandomPromptFromFile v{NODE_VERSION}: "
            f"idx={idx}/{total - 1}  name={name}"
        )

        result = (positive, negative, name, int(idx), int(prev_idx), int(total))

        return {
            "ui": {
                "yfg_pf_index_current":  (int(idx),),
                "yfg_pf_index_previous": (int(prev_idx),),
                "yfg_pf_total_count":    (int(total),),
            },
            "result": result,
        }

    @staticmethod
    def _pick(
        lo: int, hi: int, scope: str,
        random_source: str, ensure_unique: bool,
        history_size: int, time_window: int,
        retry_limit: int, use_shuffle_bag: bool,
    ) -> int:
        if lo == hi:
            return lo

        if ensure_unique and use_shuffle_bag and _ShuffleBag.can_use(lo, hi):
            bag_key   = f"bag::{scope}::{lo}::{hi}"
            candidate = lo
            for _ in range(max(1, retry_limit)):
                candidate = _ShuffleBag.next_value(bag_key, lo, hi)
                if not _UniqueHistory.is_duplicate(candidate, scope, history_size, time_window):
                    _UniqueHistory.remember(candidate, scope, history_size)
                    return candidate
            _UniqueHistory.remember(candidate, scope, history_size)
            return candidate

        candidate = lo
        for _ in range(max(1, retry_limit)):
            candidate = _rand_int(lo, hi, random_source)
            if not ensure_unique or not _UniqueHistory.is_duplicate(
                    candidate, scope, history_size, time_window):
                if ensure_unique:
                    _UniqueHistory.remember(candidate, scope, history_size)
                return candidate

        print("[YFG] RandomPromptFromFile: retry limit reached; using last candidate.")
        if ensure_unique:
            _UniqueHistory.remember(candidate, scope, history_size)
        return candidate

    @classmethod
    def IS_CHANGED(
        cls,
        prompt_file, selection_mode, index, range_start, range_end,
        last_n_only, last_n_count, random_source, ensure_unique,
        history_size, time_window_sec, retry_limit, use_shuffle_bag, **kwargs,
    ):
        if selection_mode == "random" or ensure_unique:
            return float("NaN")
        m = hashlib.sha256()
        for v in (prompt_file, selection_mode, index):
            m.update(str(v).encode())
            m.update(b"|")
        return m.hexdigest()


# ─────────────────────────── registration ─────────────────────────────────────
# Add to __init__.py:
#   from .YFGRandomPromptFromFile import YFGRandomPromptFromFile
#   NODE_CLASS_MAPPINGS["YFGRandomPromptFromFile_node"]      = YFGRandomPromptFromFile
#   NODE_DISPLAY_NAME_MAPPINGS["YFGRandomPromptFromFile_node"] = "🐯 YFG Random Prompt From File"

NODE_CLASS_MAPPINGS = {
    "YFGRandomPromptFromFile_node": YFGRandomPromptFromFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YFGRandomPromptFromFile_node": "🐯 YFG Random Prompt From File",
}
