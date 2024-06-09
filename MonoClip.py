"""
@author: YFG
@title: YFG Monochrome Image Clip
@nickname: 🐯 YFG Monochrome Image Clip
@description: This node takes an input image and generates various clipped greyscale images.
"""

## Based on original code by XSS https://civitai.com/models/24869?modelVersionId=29755 ##

import torch
import numpy as np
from PIL import Image, ImageOps

class MonoClip:
    channels = ["red", "green", "blue", "greyscale"]
    modes = ["binary", "inverse binary", "to zero", "inverse to zero", "truncate", "inverse truncate"]
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "channel": (s.channels, {"default": "greyscale"}),
                "threshold": ("INT", {
                    "default": 0, 
                    "min": 0,
                    "max": 255,
                    "step": 1
                }),
                "mode": (s.modes, {"default": "binary"})
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "mono_clip"

    CATEGORY = "🐯 YFG"

    def mono_clip(self, image, channel, mode, threshold):
        image = 255. * image[0].cpu().numpy()
        image = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
        c = channel[0].upper()
        if channel in ["red", "green", "blue"] and c in image.getbands():
            image = image.getchannel(c)
        image = ImageOps.grayscale(image)
        if mode == "binary":
            filter = lambda x: 255 if x > threshold else 0
        elif mode == "inverse binary":
            filter = lambda x: 0 if x > threshold else 255
        elif mode == "to zero":
            filter = lambda x: x if x > threshold else 0
        elif mode == "inverse to zero":
            filter = lambda x: 0 if x > threshold else x
        elif mode == "truncate":
            filter = lambda x: threshold if x > threshold else x
        else:
            filter = lambda x: x if x > threshold else threshold
        image = image.convert("L").point(filter, mode="L")
        image = image.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        
        return (image,)
