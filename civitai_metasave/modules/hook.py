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

# Save-node classes to watch for. Populated by civitai_metasave/__init__.py.
# A set rather than a single class so that V1 and V2 (and any future version)
# can share this one set of monkey-patches — patching execution.* more than
# once would make the pre-hooks fire repeatedly for every node.
_SaveNodeClasses = set()

# Backwards-compatible alias; assigning to it still works.
_SaveNodeClass = None


def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt, current_extra_data, prompt_executer
    current_prompt     = prompt
    current_extra_data = extra_data
    prompt_executer    = self


def pre_get_input_data(inputs, class_def, unique_id, *args):
    global current_save_image_node_id
    if class_def in _SaveNodeClasses:
        current_save_image_node_id = unique_id
    elif _SaveNodeClass is not None and class_def == _SaveNodeClass:
        current_save_image_node_id = unique_id
