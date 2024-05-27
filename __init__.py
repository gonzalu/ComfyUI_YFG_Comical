from .image2histograms import ImageHistogramsNode
from .image2histogramscompact import ImageHistogramsNodeCompact
from .image2halftone import ImageHalftoneNode
from .images2sidebyside import ImagesSideBySideNode
from .switchers.imageSwitchers import *

NODE_CLASS_MAPPINGS = {
    "image_histograms_node": ImageHistogramsNode,
    "image_histograms_node_compact": ImageHistogramsNodeCompact,
    "image_halftone": ImageHalftoneNode,
    "images_side_by_side": ImagesSideBySideNode,
    "Image3SwitcherNode": Image3SwitcherNode,
    "Image5SwitcherNode": Image5SwitcherNode,
    "Image10SwitcherNode": Image10SwitcherNode,
    "Image15SwitcherNode": Image15SwitcherNode,
    "Image20SwitcherNode": Image20SwitcherNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histograms_node": "\ud83d\udc2f YFG Histograms Generator",
    "image_histograms_node_compact": "\ud83d\udc2f YFG Histograms Generator (compact)",
    "image_halftone": "\ud83d\udc2f YFG Image Halftone Generator",
    "images_side_by_side": "\ud83d\udc2f YFG Image Side by Side",
    "Image3SwitcherNode": "\ud83d\udc2f YFG 3 Image Switcher",
    "Image5SwitcherNode": "\ud83d\udc2f YFG 5 Image Switcher",
    "Image10SwitcherNode": "\ud83d\udc2f YFG 10 Image Switcher",
    "Image15SwitcherNode": "\ud83d\udc2f YFG 15 Image Switcher",
    "Image20SwitcherNode": "\ud83d\udc2f YFG 20 Image Switcher",
}
print(f"\033[1;32m[YFG Comical]: 🐯 \033[93m\033[3m Loaded {len(NODE_CLASS_MAPPINGS)} nodes.\033[0m 🐯")
