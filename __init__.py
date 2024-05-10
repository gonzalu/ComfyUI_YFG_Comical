from .text_overlay import MemeGeneratorNode
from .image2histogram import ImageHistogramNode
from .image2histograms import ImageHistogramsNode
from .helloworld import HelloWorldNode

NODE_CLASS_MAPPINGS = {
    "image_histogram_node": ImageHistogramNode,
    "image_histograms_node": ImageHistogramsNode,
    "meme_generator_node": MemeGeneratorNode,
    "hello_world": HelloWorldNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histogram_node": "\ud83d\udc31 YFG Img Histograms Generator (deprecated)",
    "image_histograms_node": "\ud83d\udc31 YFG Img Histograms Generator /v2",
    "meme_generator_node": "\ud83d\udc31 YFG Meme Generator",
    "hello_world": "\ud83d\udc31 YFG Hello World",
}
