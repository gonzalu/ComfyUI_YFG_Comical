# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : 🐯 YFG CivitAI MetaSave — Package Init
# Nickname    : YFG_CivitAI_MetaSave
# Description : Sub-package init for the CivitAI MetaSave nodes inside
#               ComfyUI_YFG_Comical. Installs the PromptExecutor monkey-patch
#               ONCE and exposes both node versions.
#
#               Both versions deliberately live in this one package and share
#               modules/. Cloning the folder per version would re-apply the
#               execution monkey-patches, making the pre-hooks fire once per
#               copy on every node, and would duplicate the model hash cache.
# =============================================================================

# 1. Install execution hooks. modules/__init__.py performs the patching as an
#    import side-effect, so importing it here is what wires everything up.
from . import modules as _modules  # noqa: F401
from .modules import hook as _hook

# 2. Import the node classes
from .modules.node import YFG_CivitAI_MetaSave
from .modules.node_v2 import YFG_CivitAI_MetaSave_V2

# 3. Register every save-node class with the shared hook so it can identify
#    which node is currently executing, regardless of version.
_hook._SaveNodeClasses.update({
    YFG_CivitAI_MetaSave,
    YFG_CivitAI_MetaSave_V2,
})

__all__ = [
    "YFG_CivitAI_MetaSave",
    "YFG_CivitAI_MetaSave_V2",
]
