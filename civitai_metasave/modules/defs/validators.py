# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Node Validators
# Nickname    : YFG_CivitAI_MetaSave
# Description : Validator functions that gate whether a node's field should be
#               captured during the metadata pass. Used by CAPTURE_FIELD_LIST
#               entries that need conditional inclusion logic.
# =============================================================================

from collections import deque
from .samplers import SAMPLERS


def is_positive_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
    return node_id in _get_node_id_list(prompt, "positive")


def is_negative_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
    return node_id in _get_node_id_list(prompt, "negative")


def _get_node_id_list(prompt, field_name):
    """
    Walk sampler nodes and follow conditioning links back to CLIPTextEncode
    nodes, returning a list of node IDs that are on the positive or negative
    conditioning path.
    """
    node_id_list = {}
    for nid, node in prompt.items():
        for sampler_type, field_map in SAMPLERS.items():
            if node["class_type"] == sampler_type:
                d = deque()
                if field_name in field_map and field_map[field_name] in node["inputs"]:
                    d.append(node["inputs"][field_map[field_name]][0])
                while d:
                    nid2 = d.popleft()
                    if nid2 not in prompt:
                        continue
                    class_type = prompt[nid2]["class_type"]
                    if "CLIPTextEncode" in class_type:
                        node_id_list[nid] = nid2
                        break
                    for k, v in prompt[nid2]["inputs"].items():
                        if isinstance(v, list) and v:
                            d.append(v[0])

    return list(node_id_list.values())


def is_distinct_negative_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
    """
    Capture a negative prompt only when it is genuinely distinct from the
    positive path.  Some Flux/Ideogram workflows reuse the positive
    CLIPTextEncode on the negative side (via ConditioningZeroOut), which
    would otherwise write the positive text into the negative field.
    """
    try:
        if not is_negative_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
            return False
        if is_positive_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
            return False
    except Exception:
        return False
    return True


def is_latent_executed(node_id, obj, prompt, extra_data, outputs, input_data_all):
    """Return True if a LatentUpscaleBy node has actually executed (latent tensor present)."""
    try:
        samples = input_data_all[0]["samples"][0]["samples"]
        return samples is not None
    except (KeyError, IndexError, TypeError, AttributeError):
        return False


def is_primary_unet_model(node_id, obj, prompt, extra_data, outputs, input_data_all):
    """
    Skip unconditional / negative-side UNETs when capturing the primary model.
    Ideogram 4 and similar dual-model workflows use two UNETLoader nodes;
    we skip the one whose name contains 'unconditional'.
    """
    try:
        value = input_data_all[0].get("unet_name")
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str) and "unconditional" in value.lower():
            return False
    except Exception:
        pass
    return True
