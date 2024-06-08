"""
@version: 1.0.11
@author: YFG
@title: Image Size Node
@nickname: 🐯 Image Size
@description: This node calculates the dimensions of an input image and displays the width and height.
"""
import os
import hashlib
import folder_paths
import torch
import numpy as np
import comfy.utils
from server import PromptServer
from nodes import MAX_RESOLUTION
from PIL import Image, ImageDraw, ImageFilter
from torchvision.transforms import Resize, CenterCrop, GaussianBlur
from torchvision.transforms.functional import to_pil_image

from .libs.image import pil2tensor, tensor2pil, ResizeMode, get_new_bounds, RGB2RGBA, image2mask

class ImageToBase64Node:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width_int", "height_int")
    OUTPUT_NODE = True
    FUNCTION = "image_width_height"
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "🐯 YFG"

    def image_width_height(self, image):
        _, raw_H, raw_W, _ = image.shape

        width = raw_W
        height = raw_H

        if width is not None and height is not None:
            result = (width, height)
        else:
            result = (0, 0)
        
        return (width, height)  # This should be a tuple of integers



class PreviewTextNode:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {        
                "text": ("STRING", {"forceInput": True}),     
                },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
            }

    RETURN_TYPES = ("STRING",)
    OUTPUT_NODE = True
    FUNCTION = "preview_text"

    CATEGORY = "AlekPet Nodes/extras"

    def preview_text(self, text, prompt=None, extra_pnginfo=None):
        return {"ui": {"string": [text,]}, "result": (text,)}
