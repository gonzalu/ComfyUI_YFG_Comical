# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : 🐯 YFG CivitAI MetaSave — Package Init
# Nickname    : YFG_CivitAI_MetaSave
# Description : Sub-package init for the CivitAI MetaSave node inside
#               ComfyUI_YFG_Comical.  Installs the PromptExecutor monkey-patch
#               and exposes the YFG_CivitAI_MetaSave node class for import by
#               the top-level __init__.py.
# =============================================================================

# 1. Install execution hooks (monkey-patches PromptExecutor.execute and
#    get_input_data so the metadata capture pipeline can observe live graphs)
from . import modules as _modules  # noqa – side-effect: installs prefix_function wraps
from .modules import hook as _hook  # noqa

# 2. Import the node class
from .modules.node import YFG_CivitAI_MetaSave

# 3. Tell the hook which class to track for the save-node ID
_hook._SaveNodeClass = YFG_CivitAI_MetaSave

__all__ = ["YFG_CivitAI_MetaSave"]
