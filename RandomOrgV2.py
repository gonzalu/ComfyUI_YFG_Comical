"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
"""

## Based on original idea by Jordan Thompson (WASasquatch) https://github.com/WASasquatch/was-node-suite-comfyui ##
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to
# deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import annotations

import os
import json
import hashlib
import requests
from typing import List, Dict, Any, Tuple, Optional

# -----------------------------------------------------------------------------
# API KEY STORAGE (no UI field)
# -----------------------------------------------------------------------------

NODE_VERSION = "2.0.1"  # bump however you want; this node file previously didn't version explicitly
API_KEY_FILENAME = "random_org_api_key.json"


def _load_api_key() -> Optional[str]:
    # 1) Env var wins for easy local development
    env_key = os.getenv("RANDOM_ORG_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 2) Local JSON file next to this script
    here = os.path.dirname(os.path.realpath(__file__))
    key_path = os.path.join(here, API_KEY_FILENAME)
    try:
        with open(key_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = (data or {}).get("api_key", "").strip()
        return key if key else None
    except FileNotFoundError:
        print(f"RandomOrgV2: API key file not found: {key_path}")
    except json.JSONDecodeError as e:
        print(f"RandomOrgV2: Failed to parse {API_KEY_FILENAME}: {e}")
    except Exception as e:
        print(f"RandomOrgV2: Unexpected error reading key file: {e}")
    return None


class _ShuffleBag:
    """
    Shuffle-bag (sampling without replacement).
    For each bag_key we maintain a shuffled list of remaining values.
    When empty or when range changes, refill + reshuffle.
    """
    # bag_key -> {"remaining": [int,...], "last_size": int}
    _bags: Dict[str, Dict[str, Any]] = {}

    # Guardrail: don't build a bag bigger than this many items.
    # If a user sets min/max to a massive span, we fall back to history de-dup.
    MAX_BAG_SIZE = 200_000

    @classmethod
    def can_use(cls, lo: int, hi: int) -> bool:
        n = (hi - lo + 1)
        return 1 <= n <= cls.MAX_BAG_SIZE

    @classmethod
    def _get_bag(cls, bag_key: str) -> Dict[str, Any]:
        if bag_key not in cls._bags:
            cls._bags[bag_key] = {"remaining": [], "last_size": -1}
        return cls._bags[bag_key]

    @classmethod
    def next_value(cls, bag_key: str, lo: int, hi: int) -> int:
        bag = cls._get_bag(bag_key)
        size = hi - lo + 1

        if bag["last_size"] != size or not bag["remaining"]:
            values = list(range(lo, hi + 1))
            # Local cryptographic shuffle; avoids hammering random.org
            import random
            random.SystemRandom().shuffle(values)
            bag["remaining"] = values
            bag["last_size"] = size

        return int(bag["remaining"].pop(0))


class RandomOrgV2TrueRandomNumber:
    """
    True Random Number Generator (V2) via random.org.
    """

    DESCRIPTION = (
        f"Random.org True Random Number (V2) (v{NODE_VERSION})\n\n"
        "Generates a true random integer using random.org.\n\n"
        "Uniqueness options:\n"
        "  • ensure_unique=true + use_shuffle_bag=true: uses a shuffle-bag (no repeats until the range is exhausted, then reshuffles).\n"
        "  • If the range is very large, the node automatically falls back to history-based de-dup to avoid huge memory use.\n\n"
        "API Key:\n"
        "  • Set env var RANDOM_ORG_API_KEY, or create random_org_api_key.json next to this file: {\"api_key\":\"...\"}\n"
    )

    # Output hover tips (one per RETURN_TYPES/RETURN_NAMES order)
    OUTPUT_TOOLTIPS = (
        "ComfyUI NUMBER output (typically behaves like a float).",
        "Same value as a Python float.",
        "Same value as a Python int.",
    )

    # ---- Class-level caches (persist for the lifetime of the Python process) ----
    # Global cache: value -> last_timestamp
    _global_map = {}
    _global_order = []  # FIFO

    # Per-range caches: key (min,max) -> {"map": {value: t}, "order": [values FIFO]}
    _range_caches = {}

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # Include both tooltip+description; different frontends have historically used one or the other.
        return {
            "required": {
                "minimum": ("FLOAT", {
                    "default": 0,
                    "min": -9223372036854775808,
                    "max": 9223372036854775807,
                    "tooltip": "Lower bound (inclusive). Floats are converted to integers via int().",
                    "description": "Lower bound (inclusive). Floats are converted to integers via int().",
                }),
                "maximum": ("FLOAT", {
                    "default": 10,
                    "min": -9223372036854775808,
                    "max": 9223372036854775807,
                    "tooltip": "Upper bound (inclusive). Floats are converted to integers via int().",
                    "description": "Upper bound (inclusive). Floats are converted to integers via int().",
                }),
                "mode": (["random", "fixed"], {
                    "default": "random",
                    "tooltip": "random: call random.org. fixed: return minimum deterministically (cacheable).",
                    "description": "random: call random.org. fixed: return minimum deterministically (cacheable).",
                }),
            },
            "optional": {
                # Uniqueness controls
                "ensure_unique": ("BOOLEAN", {
                    "default": True,  # ✅ requested
                    "label": "Avoid repeats?",
                    "tooltip": "If true, avoids repeats using shuffle-bag (preferred) or history de-dup (fallback).",
                    "description": "If true, avoids repeats using shuffle-bag (preferred) or history de-dup (fallback).",
                }),
                "unique_scope": (["range", "global"], {
                    "default": "range",
                    "label": "Unique scope",
                    "tooltip": "range: uniqueness tracked per (minimum,maximum). global: shared across all ranges.",
                    "description": "range: uniqueness tracked per (minimum,maximum). global: shared across all ranges.",
                }),
                "history_size": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 100000,
                    "label": "Unique history size",
                    "tooltip": "Used by history-based de-dup (and as extra guard when global scope is enabled).",
                    "description": "Used by history-based de-dup (and as extra guard when global scope is enabled).",
                }),
                "time_window_sec": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 86400,
                    "label": "Unique time window (sec, 0=off)",
                    "tooltip": "If >0, values older than this many seconds are forgotten for de-dup checks.",
                    "description": "If >0, values older than this many seconds are forgotten for de-dup checks.",
                }),
                "retry_limit": ("INT", {
                    "default": 20,
                    "min": 0,
                    "max": 1000,
                    "label": "Retry attempts on duplicate",
                    "tooltip": "How many times to try finding a non-duplicate when using history-based de-dup (or global checks).",
                    "description": "How many times to try finding a non-duplicate when using history-based de-dup (or global checks).",
                }),
                "use_shuffle_bag": ("BOOLEAN", {
                    "default": True,
                    "label": "Use shuffle-bag (no repeats until exhausted)",
                    "tooltip": f"If true and range size <= {_ShuffleBag.MAX_BAG_SIZE:,}, use shuffle-bag. Otherwise fall back.",
                    "description": f"If true and range size <= {_ShuffleBag.MAX_BAG_SIZE:,}, use shuffle-bag. Otherwise fall back.",
                }),
            }
        }

    RETURN_TYPES = ("NUMBER", "FLOAT", "INT")
    RETURN_NAMES = ("number", "float", "int")
    FUNCTION = "return_true_random_number"
    CATEGORY = "🐯 YFG/🔢 Numbers"

    def return_true_random_number(
        self,
        minimum: float,
        maximum: float,
        mode: str = "random",
        ensure_unique: bool = True,
        unique_scope: str = "range",
        history_size: int = 100,
        time_window_sec: int = 0,
        retry_limit: int = 20,
        use_shuffle_bag: bool = True,
    ):
        api_key = _load_api_key()
        if not api_key:
            print("RandomOrgV2: No API key available. Create random_org_api_key.json or set RANDOM_ORG_API_KEY.")
            number = 0
            return (number, float(number), int(number))

        # Normalize and validate bounds
        lo = int(minimum)
        hi = int(maximum)
        if hi < lo:
            print(f"RandomOrgV2: Swapping min/max since maximum < minimum ({hi} < {lo}).")
            lo, hi = hi, lo

        # If mode is fixed, always return the minimum (deterministic)
        if mode == "fixed":
            number = lo
            return (number, float(number), int(number))

        span = hi - lo + 1

        # Fast path: uniqueness off OR trivial range
        if (not ensure_unique) or span <= 1:
            nums = self._get_random_integers(api_key=api_key, amount=1, minimum=lo, maximum=hi)
            number = nums[0]
            return (number, float(number), int(number))

        # ----------------------------
        # Uniqueness-enabled path
        # ----------------------------

        # Prefer shuffle-bag when range size is reasonable.
        # This guarantees "no repeats until exhausted".
        if use_shuffle_bag and _ShuffleBag.can_use(lo, hi):
            # Bag key incorporates scope + range
            bag_key = f"{unique_scope}::{lo}::{hi}"

            candidate = _ShuffleBag.next_value(bag_key=bag_key, lo=lo, hi=hi)

            # If unique_scope is global, also honor global history rules to avoid collisions
            # across different ranges that share the same numeric value.
            if unique_scope == "global":
                range_key = (lo, hi)
                tries = 0
                max_tries = max(1, int(retry_limit))
                while tries < max_tries and self._is_duplicate(candidate, range_key, unique_scope, history_size, time_window_sec):
                    candidate = _ShuffleBag.next_value(bag_key=bag_key, lo=lo, hi=hi)
                    tries += 1

            self._remember(candidate, (lo, hi), unique_scope, history_size)
            return (candidate, float(candidate), int(candidate))

        # Fallback: history-based de-dup (kept for very large ranges)
        key = (lo, hi)
        candidate = lo  # init for safety
        for _ in range(max(1, int(retry_limit))):
            nums = self._get_random_integers(api_key=api_key, amount=1, minimum=lo, maximum=hi)
            candidate = nums[0]
            if not self._is_duplicate(candidate, key, unique_scope, history_size, time_window_sec):
                self._remember(candidate, key, unique_scope, history_size)
                return (candidate, float(candidate), int(candidate))

        print("RandomOrgV2: Retry limit reached while avoiding duplicates; emitting last value.")
        self._remember(candidate, key, unique_scope, history_size)
        return (candidate, float(candidate), int(candidate))

    # --- Internal helpers ---
    def _get_random_integers(self, api_key: str, amount: int, minimum: int, maximum: int) -> List[int]:
        payload = {
            "jsonrpc": "2.0",
            "method": "generateIntegers",
            "params": {
                "apiKey": api_key,
                "n": int(amount),
                "min": int(minimum),
                "max": int(maximum),
                "replacement": True,
                "base": 10
            },
            "id": 1
        }

        try:
            resp = requests.post(
                "https://api.random.org/json-rpc/2/invoke",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=20,
            )
        except requests.RequestException as e:
            print(f"RandomOrgV2: Network error contacting random.org: {e}")
            return [0]

        if resp.status_code != 200:
            print(f"RandomOrgV2: HTTP {resp.status_code} from random.org")
            return [0]

        try:
            data = resp.json()
        except ValueError:
            print("RandomOrgV2: Failed to decode JSON from random.org response")
            return [0]

        if "error" in data:
            print(f"RandomOrgV2: API error: {data['error']}")
            return [0]

        try:
            return data["result"]["random"]["data"]
        except Exception as e:
            print(f"RandomOrgV2: Unexpected response format: {e}")
            return [0]

    @staticmethod
    def _now() -> float:
        try:
            import time
            return time.time()
        except Exception:
            return 0.0

    def _get_range_cache(self, key: Tuple[int, int]):
        cache = self._range_caches.get(key)
        if cache is None:
            cache = {"map": {}, "order": []}
            self._range_caches[key] = cache
        return cache

    def _prune(self, ordered_list, value_map, history_size, time_window_sec):
        while len(ordered_list) > history_size:
            oldest = ordered_list.pop(0)
            value_map.pop(oldest, None)
        if time_window_sec and time_window_sec > 0:
            now = self._now()
            for v in list(ordered_list):
                ts = value_map.get(v)
                if ts is None:
                    continue
                if now - ts > time_window_sec:
                    ordered_list.remove(v)
                    value_map.pop(v, None)

    def _is_duplicate(self, value: int, range_key: Tuple[int, int], scope: str, history_size: int, time_window_sec: int) -> bool:
        now = self._now()
        if scope == "global":
            self._prune(self._global_order, self._global_map, history_size, time_window_sec)
            ts = self._global_map.get(value)
            if ts is None:
                return False
            if time_window_sec and time_window_sec > 0 and (now - ts) > time_window_sec:
                return False
            return True
        else:
            cache = self._get_range_cache(range_key)
            self._prune(cache["order"], cache["map"], history_size, time_window_sec)
            ts = cache["map"].get(value)
            if ts is None:
                return False
            if time_window_sec and time_window_sec > 0 and (now - ts) > time_window_sec:
                return False
            return True

    def _remember(self, value: int, range_key: Tuple[int, int], scope: str, history_size: int):
        now = self._now()
        if scope == "global":
            self._global_map[value] = now
            self._global_order.append(value)
            self._prune(self._global_order, self._global_map, history_size, 0)
        else:
            cache = self._get_range_cache(range_key)
            cache["map"][value] = now
            cache["order"].append(value)
            self._prune(cache["order"], cache["map"], history_size, 0)

    @classmethod
    def IS_CHANGED(
        cls,
        mode: str,
        minimum: float,
        maximum: float,
        ensure_unique: bool = True,
        unique_scope: str = "range",
        history_size: int = 100,
        time_window_sec: int = 0,
        retry_limit: int = 20,
        use_shuffle_bag: bool = True,
        **kwargs
    ):
        # If mode is 'fixed', return a stable hash so ComfyUI can cache the node's output.
        if mode == "fixed":
            m = hashlib.sha256()
            m.update(
                f"{mode}|{minimum}|{maximum}|{ensure_unique}|{unique_scope}|{history_size}|"
                f"{time_window_sec}|{retry_limit}|{use_shuffle_bag}".encode("utf-8")
            )
            return m.hexdigest()
        return float("nan")


# --- ComfyUI registration ---
NODE_CLASS_MAPPINGS = {
    "RandomOrgV2TrueRandomNumber": RandomOrgV2TrueRandomNumber,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomOrgV2TrueRandomNumber": "Random.org True Random Number (V2)",
}
