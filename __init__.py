from .image2histograms import ImageHistogramsNode
from .image2histogramscompact import ImageHistogramsNodeCompact 

NODE_CLASS_MAPPINGS = {
    "image_histograms_node": ImageHistogramsNode,
    "image_histograms_node_compact": ImageHistogramsNodeCompact,    
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histograms_node": "\ud83d\udc31 YFG Histograms Generator",
    "image_histograms_node_compact": "\ud83d\udc31 YFG Histograms Generator (compact)",
}
