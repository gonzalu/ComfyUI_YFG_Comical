# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Sampler Node Definitions
# Nickname    : YFG_CivitAI_MetaSave
# Description : Maps known ComfyUI sampler node class names to their
#               positive/negative conditioning input field names.
#               Used by the tracer to locate sampler nodes in the graph.
# =============================================================================

SAMPLERS = {
    "KSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerAdvanced": {
        "positive": "positive",
        "negative": "negative",
    },
    # Flux / SD3 / modern guider-based samplers
    "SamplerCustomAdvanced": {
        "positive": "guider",
    },
    "SamplerCustom": {
        "positive": "positive",
        "negative": "negative",
    },
    # Guider nodes that sit between SamplerCustomAdvanced and CLIPTextEncode
    "CFGGuider": {
        "positive": "positive",
    },
    "DualModelGuider": {
        "positive": "positive",
        "negative": "negative",
    },
}
