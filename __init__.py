from .py._nodes.memeGenerator_v1 import MemeGenerator_v1
from .py._nodes.image2histogram_v1 import ImageHistogram_v1
from .py._nodes.image2histograms_v2 import ImageHistograms_v2
from .py._nodes.image2histograms_compact_v1 import ImageHistogramsCompact_v1 

NODE_CLASS_MAPPINGS = {
    "image_histograms_node_v2": ImageHistograms_v2,
    "image_histograms_compact_node_v1": ImageHistogramsCompact_v1,    
    "meme_generator_node_v1": MemeGenerator_v1,

    "image_histogram_node": ImageHistogram_v1,
    "image_histogram_node_v1": ImageHistogram_v1,
    "image_histograms_node": ImageHistograms_v2,
    "image_histograms_self_node": ImageHistogramsCompact_v1,    
    "meme_generator_node": MemeGenerator_v1,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histograms_node_v2": "\ud83d\udc31 YFG Histograms Generator /v2",
    "image_histograms_compact_node_v1": "\ud83d\udc31 YFG Histograms Generator Compact /V1",  # Update this with a meaningful display name
    "meme_generator_node_v1": "\ud83d\udc31 YFG Meme Generator v1",

    "image_histogram_node": "\ud83d\udc31 YFG Histograms Generator (deprecated)",
    "image_histogram_node_v1": "\ud83d\udc31 YFG Histograms Generator v1 (deprecated)",
    "image_histograms_node": "\ud83d\udc31 YFG Histograms Generator /v2 (deprecated)",
    "image_histograms_self_node": "\ud83d\udc31 YFG Histograms Generator Compact (deprecated) /V1",  # Update this with a meaningful display name
    "meme_generator_node": "\ud83d\udc31 YFG Meme Generator (deprecated)",
}
