from .text_overlay import MemeGeneratorNode
from .image2histogram import ImageHistogramNode
from .helloworld import HelloWorldNode

NODE_CLASS_MAPPINGS = {
    "image_histogram_node": ImageHistogramNode,
    "meme_generator_node": MemeGeneratorNode,
    "hello_world": HelloWorldNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histogram_node": "YFG - Image Histogram Generator",
    "meme_generator_node": "YFG - Comical Meme Generator",
    "hello_world": "YFG - Print Hello World",
}
