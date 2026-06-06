# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Execution Hook
# Nickname    : YFG_CivitAI_MetaSave
# Description : Monkey-patches ComfyUI's PromptExecutor.execute() and
#               get_input_data() to capture the live prompt, extra data,
#               executor reference, and current save-node ID at generation
#               time, making them available to the metadata capture pipeline.
# =============================================================================

# Global state populated by the hooks at execution time
current_prompt           = {}
current_extra_data       = {}
prompt_executer          = None
current_save_image_node_id = -1

# Populated after node.py is imported (set by modules/__init__.py)
_SaveNodeClass = None


def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt, current_extra_data, prompt_executer
    current_prompt     = prompt
    current_extra_data = extra_data
    prompt_executer    = self


def pre_get_input_data(inputs, class_def, unique_id, *args):
    global current_save_image_node_id
    if _SaveNodeClass is not None and class_def == _SaveNodeClass:
        current_save_image_node_id = unique_id
