# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Config
# Nickname    : YFG_CivitAI_MetaSave
# Description : Path configuration for the node's on-disk cache directory.
# =============================================================================

import os

MODULES_ROOT_DIR  = os.path.dirname(__file__)           # civitai_metasave/modules/
SUBPACKAGE_DIR    = os.path.abspath(os.path.join(MODULES_ROOT_DIR, ".."))   # civitai_metasave/
NODE_CACHE_DIR    = os.path.join(SUBPACKAGE_DIR, ".cache")

os.makedirs(NODE_CACHE_DIR, exist_ok=True)
