# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Modules Package Init
# Nickname    : YFG_CivitAI_MetaSave
# Description : Installs the pre-execution hooks by monkey-patching
#               ComfyUI's PromptExecutor.execute() and get_input_data()
#               so the metadata capture pipeline can observe the live graph.
# =============================================================================

import functools
import execution

from . import hook
from .hook import pre_execute, pre_get_input_data


def prefix_function(function, prefunction):
    """Wrap *function* so that *prefunction* always runs first."""
    @functools.wraps(function)
    def run(*args, **kwargs):
        prefunction(*args, **kwargs)
        return function(*args, **kwargs)
    return run


execution.PromptExecutor.execute = prefix_function(
    execution.PromptExecutor.execute, pre_execute
)

execution.get_input_data = prefix_function(
    execution.get_input_data, pre_get_input_data
)
