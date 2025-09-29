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
from typing import List

# -----------------------------------------------------------------------------
# API KEY STORAGE (no UI field)
# -----------------------------------------------------------------------------
# The node reads your Random.org API key from a local JSON file that lives
# next to this Python file. This prevents the key from being embedded in
# workflow JSON or image metadata.
#
# File name: random_org_api_key.json
# Format:
# {
#   "api_key": "YOUR_API_KEY_HERE"
# }
#
# You can also set an environment variable RANDOM_ORG_API_KEY to override.
# The node will NEVER write or overwrite the key file.
# -----------------------------------------------------------------------------

API_KEY_FILENAME = "random_org_api_key.json"


def _load_api_key() -> str | None:
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


class RandomOrgV2TrueRandomNumber:
    """True Random Number Generator (V2) via random.org

    Outputs three ports to maximize compatibility with downstream nodes:
    - NUMBER (ComfyUI generic numeric)
    - FLOAT (Python float)
    - INT (Python int)

    This node does NOT expose the API key in the UI. Provide the key via:
    - Environment variable RANDOM_ORG_API_KEY, or
    - A JSON file named 'random_org_api_key.json' next to this file.

    Optional de-duplication: enable `ensure_unique` to avoid emitting a value
    that was recently produced. You can scope uniqueness to the current range
    (min/max) or globally, and control history size and/or a time window.
    """

    # ---- Class-level caches (persist for the lifetime of the Python process) ----
    # Global cache: value -> last_timestamp
    _global_map = {}
    _global_order = []  # simple list as FIFO; we prune when exceeding size

    # Per-range caches: key (min,max) -> {"map": {value: t}, "order": [values in FIFO]}
    _range_caches = {}

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "minimum": ("FLOAT", {"default": 0, "min": -9223372036854775808, "max": 9223372036854775807}),
                "maximum": ("FLOAT", {"default": 10, "min": -9223372036854775808, "max": 9223372036854775807}),
                "mode": (["random", "fixed"],),
            },
            "optional": {
                # Uniqueness controls (OFF by default to preserve exact random.org behavior)
                "ensure_unique": ("BOOLEAN", {"default": False, "label": "Avoid repeats?"}),
                "unique_scope": (["range", "global"], {"default": "range", "label": "Unique scope"}),
                "history_size": ("INT", {"default": 100, "min": 1, "max": 100000, "label": "Unique history size"}),
                "time_window_sec": ("INT", {"default": 0, "min": 0, "max": 86400, "label": "Unique time window (sec, 0=off)"}),
                "retry_limit": ("INT", {"default": 20, "min": 0, "max": 1000, "label": "Retry attempts on duplicate"}),
            }
        }

    RETURN_TYPES = ("NUMBER", "FLOAT", "INT")
    FUNCTION = "return_true_random_number"
    CATEGORY = "🐯 YFG/🔢 Numbers"

    def return_true_random_number(self, minimum: float, maximum: float, mode: str = "random",
                                  ensure_unique: bool = False, unique_scope: str = "range",
                                  history_size: int = 100, time_window_sec: int = 0, retry_limit: int = 20):
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

        # Fast path (no uniqueness requested)
        if not ensure_unique or (hi - lo + 1) <= 1:
            nums = self._get_random_integers(api_key=api_key, amount=1, minimum=lo, maximum=hi)
            number = nums[0]
            return (number, float(number), int(number))

        # Uniqueness-enabled path
        key = (lo, hi)
        for _ in range(max(1, retry_limit)):
            nums = self._get_random_integers(api_key=api_key, amount=1, minimum=lo, maximum=hi)
            candidate = nums[0]
            if not self._is_duplicate(candidate, key, unique_scope, history_size, time_window_sec):
                self._remember(candidate, key, unique_scope, history_size)
                return (candidate, float(candidate), int(candidate))
        # If we reach here, we failed to find a unique value within retry limit; emit last candidate
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

        # random.org error response handling
        if "error" in data:
            print(f"RandomOrgV2: API error: {data['error']}")
            return [0]

        try:
            return data["result"]["random"]["data"]
        except Exception as e:
            print(f"RandomOrgV2: Unexpected response format: {e}")
            return [0]

    @staticmethod
    def _now():
        try:
            import time
            return time.time()
        except Exception:
            return 0.0

    def _get_range_cache(self, key):
        cache = self._range_caches.get(key)
        if cache is None:
            cache = {"map": {}, "order": []}
            self._range_caches[key] = cache
        return cache

    def _prune(self, ordered_list, value_map, history_size, time_window_sec):
        # Size-based pruning
        while len(ordered_list) > history_size:
            oldest = ordered_list.pop(0)
            value_map.pop(oldest, None)
        # Time-based pruning (if enabled)
        if time_window_sec and time_window_sec > 0:
            now = self._now()
            # Iterate a copy to safely remove while iterating
            for v in list(ordered_list):
                ts = value_map.get(v)
                if ts is None:
                    continue
                if now - ts > time_window_sec:
                    ordered_list.remove(v)
                    value_map.pop(v, None)

    def _is_duplicate(self, value, range_key, scope, history_size, time_window_sec):
        now = self._now()
        if scope == "global":
            # Time-based prune first, then test
            self._prune(self._global_order, self._global_map, history_size, time_window_sec)
            ts = self._global_map.get(value)
            if ts is None:
                return False
            if time_window_sec and time_window_sec > 0 and (now - ts) > time_window_sec:
                return False
            return True
        else:  # scope == 'range'
            cache = self._get_range_cache(range_key)
            self._prune(cache["order"], cache["map"], history_size, time_window_sec)
            ts = cache["map"].get(value)
            if ts is None:
                return False
            if time_window_sec and time_window_sec > 0 and (now - ts) > time_window_sec:
                return False
            return True

    def _remember(self, value, range_key, scope, history_size):
        now = self._now()
        if scope == "global":
            # record
            self._global_map[value] = now
            self._global_order.append(value)
            # prune on size only here; time pruning happens on check
            self._prune(self._global_order, self._global_map, history_size, 0)
        else:
            cache = self._get_range_cache(range_key)
            cache["map"][value] = now
            cache["order"].append(value)
            self._prune(cache["order"], cache["map"], history_size, 0)

    @classmethod
    def IS_CHANGED(cls, mode: str, minimum: float, maximum: float, ensure_unique: bool = False,
                   unique_scope: str = "range", history_size: int = 100, time_window_sec: int = 0,
                   retry_limit: int = 20, **kwargs):
        """If mode is 'fixed', return a stable hash so ComfyUI can cache the node's output.
        We avoid hashing any secret material; include only configuration.
        """
        if mode == "fixed":
            m = hashlib.sha256()
            m.update(f"{mode}|{minimum}|{maximum}|{ensure_unique}|{unique_scope}|{history_size}|{time_window_sec}|{retry_limit}".encode("utf-8"))
            return m.hexdigest()
        return float("nan")


# --- ComfyUI registration ---
NODE_CLASS_MAPPINGS = {
    "RandomOrgV2TrueRandomNumber": RandomOrgV2TrueRandomNumber,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomOrgV2TrueRandomNumber": "Random.org True Random Number (V2)",
}
