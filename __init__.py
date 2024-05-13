from .text_overlay import MemeGeneratorNode
from .image2histogram import ImageHistogramNode
from .image2histograms import ImageHistogramsNode
from .image2histogramsSelf import ImageHistogramsSelfNode 
# from .helloworld import HelloWorldNode

NODE_CLASS_MAPPINGS = {
    "image_histogram_node": ImageHistogramNode,
    "image_histograms_node": ImageHistogramsNode,
    "image_histograms_self_node": ImageHistogramsSelfNode,    
    "meme_generator_node": MemeGeneratorNode,
    # "hello_world": HelloWorldNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histogram_node": "\ud83d\udc31 YFG Histograms Generator (deprecated)",
    "image_histograms_node": "\ud83d\udc31 YFG Histograms Generator /v2",
    "image_histograms_self_node": "\ud83d\udc31 YFG Histograms Generator (compact) /V2",  # Update this with a meaningful display name
    "meme_generator_node": "\ud83d\udc31 YFG Meme Generator",
    # "hello_world": "\ud83d\udc31 YFG Hello World",
}
