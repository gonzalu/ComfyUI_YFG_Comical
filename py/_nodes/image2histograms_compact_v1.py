"""
@author: YFG
@title: YFG Histograms
@nickname: YFG Histograms
@description: This extension calculates the histogram of an image and outputs the results as graph images for individual channels as well as RGB and Luminosity.
"""
from math import ceil, sqrt
import torch
from PIL import Image, PngImagePlugin
import numpy as np
from typing import List
import os
import random
import json
import folder_paths
from comfy.cli_args import args

from ..inc.histogram import *

class ImageHistogramsCompact_v1(ImageHistogramUtils):
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "histogram_type": (["RGB Histogram Filled", "RGB Histogram Lines", "Red Channel", "Green Channel", "Blue Channel", "Luminosity"], {"default": "RGB Histogram Filled"}),
                "histogram_size": (["small", "medium", "large"], {"default": "medium"}),
                "preview": ("BOOLEAN", {"default": True}),
                "display": (["histogram", "original"], {"default": "histogram"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    OUTPUT_NODE = True
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("Original Image", "Histogram")
    CATEGORY = "YFG"

    def generate(self, image: torch.Tensor, histogram_type="RGB Histogram Filled", histogram_size="medium", preview=True, display="histogram", prompt=None, extra_pnginfo=None):
        if image.size(0) == 0:
            return (torch.zeros(0),)

        original_image = tensor2pil(image)  # Directly pass through the original image

        # Set histogram resolution based on the input size
        dpi = {'small': 50, 'medium': 100, 'large': 150}.get(histogram_size, 100)

        # Prepare histograms
        image_array = np.array(original_image[0])

        histogram_func = {
            "RGB Histogram Filled": self.generate_filled_histogram,
            "RGB Histogram Lines": self.generate_line_histogram,
            "Red Channel": lambda img, dpi: self.generate_channel_histogram(img, 2, 'red', dpi),
            "Green Channel": lambda img, dpi: self.generate_channel_histogram(img, 1, 'green', dpi),
            "Blue Channel": lambda img, dpi: self.generate_channel_histogram(img, 0, 'blue', dpi),
            "Luminosity": self.generate_luminosity_histogram,
        }.get(histogram_type, self.generate_filled_histogram)

        histogram = histogram_func(image_array, dpi)

        # Save histogram image
        save_result = self.save_images([histogram], filename_prefix="ComfyUI", prompt=prompt, extra_pnginfo=extra_pnginfo)

        ui_images = []
        if preview:
            if display == "original":
                original_image_result = self.save_images(original_image, filename_prefix="ComfyUI_Original", prompt=prompt, extra_pnginfo=extra_pnginfo)
                ui_images.append({"filename": original_image_result["ui"]["images"][0]["filename"], "type": self.type, "subfolder": original_image_result["ui"]["images"][0]["subfolder"]})
            else:
                ui_images.append({"filename": save_result["ui"]["images"][0]["filename"], "type": self.type, "subfolder": save_result["ui"]["images"][0]["subfolder"]})

        return {
            "ui": {"images": ui_images},
            "result": (
                pil2tensor(original_image),
                pil2tensor([histogram]),
            ),
        }

    def save_images(self, images: List[Image.Image], filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].size[0], images[0].size[1])
        results = list()
        for batch_number, image in enumerate(images):
            metadata = None
            if not args.disable_metadata:
                metadata = PngImagePlugin.PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            image.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1
        return {"ui": {"images": results}}

## end
