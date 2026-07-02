# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Hash Calculator & Cache
# Nickname    : YFG_CivitAI_MetaSave
# Description : Computes SHA-256 (first 10 hex chars) hashes for model files
#               with a dual-layer in-memory + disk LRU cache to avoid
#               redundant hashing on repeat runs.
# =============================================================================

import hashlib
import threading
import os
import json
from collections import OrderedDict

from ..config import NODE_CACHE_DIR
from .log import print_warning, print_error

CACHE_FILE = os.path.join(NODE_CACHE_DIR, "model_hash_cache.json")
CACHE_SIZE_LIMIT = 100

cache_model_hash = OrderedDict()
_disk_cache = {}
_disk_cache_dirty = False
_cache_lock = threading.Lock()

# Load cache from file on startup
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            _disk_cache = json.load(f)
    except Exception as e:
        print_error(f"Failed to load cache file {CACHE_FILE}: {e}")
        _disk_cache = {}


def get_file_mod_time(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0


def trim_disk_cache():
    global _disk_cache
    if len(_disk_cache) > CACHE_SIZE_LIMIT:
        _disk_cache = dict(list(_disk_cache.items())[-CACHE_SIZE_LIMIT:])


def save_disk_cache():
    global _disk_cache_dirty
    if not _disk_cache_dirty:
        return
    try:
        trim_disk_cache()
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        temp_file = CACHE_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(_disk_cache, f, indent=2)
        os.replace(temp_file, CACHE_FILE)  # Atomic write
        _disk_cache_dirty = False
    except Exception as e:
        print_error(f"Failed to write cache to {CACHE_FILE}: {e}")


def calc_hash(filename, use_only_filename=True):
    global _disk_cache_dirty

    if not filename or not os.path.isfile(filename):
        print_warning(f"calc_hash: File not found or invalid path: {filename}")
        return ""

    key = os.path.basename(filename) if use_only_filename else filename
    current_mod_time = get_file_mod_time(filename)

    with _cache_lock:
        if key in cache_model_hash:
            return cache_model_hash[key]

        record = _disk_cache.get(key)
        if record and record.get("file_modification_date") == current_mod_time:
            cache_model_hash[key] = record["file_hash"]
            cache_model_hash.move_to_end(key)
            return record["file_hash"]

    try:
        sha256_hash = hashlib.sha256()
        with open(filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        model_hash = sha256_hash.hexdigest()[:10]

        with _cache_lock:
            if len(cache_model_hash) >= CACHE_SIZE_LIMIT:
                cache_model_hash.popitem(last=False)
            cache_model_hash[key] = model_hash

            if key not in _disk_cache or _disk_cache[key].get("file_modification_date") != current_mod_time:
                _disk_cache[key] = {
                    "file_hash": model_hash,
                    "file_modification_date": current_mod_time
                }
                _disk_cache_dirty = True

            if _disk_cache_dirty:
                save_disk_cache()

        return model_hash
    except Exception as e:
        print_error(f"Failed to calculate hash for {filename}: {e}")
        return ""
