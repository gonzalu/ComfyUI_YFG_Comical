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
import cv2 as cv
from matplotlib import pyplot as plt
from io import BytesIO
from typing import List, Union
import os
import random
import json
import folder_paths
from comfy.cli_args import args

def hex_to_rgb(hex_color):
    try:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        log.error(f"Invalid hex color: {hex_color}")
        return (0, 0, 0)

def pil2tensor(image: Union[Image.Image, List[Image.Image]]) -> torch.Tensor:
    if isinstance(image, list):
        return torch.cat([pil2tensor(img) for img in image], dim=0)
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def tensor2pil(image: torch.Tensor) -> List[Image.Image]:
    batch_count = image.size(0) if len(image.shape) > 3 else 1
    if batch_count > 1:
        out = []
        for i in range(batch_count):
            out.extend(tensor2pil(image[i]))
        return out
    return [Image.fromarray(np.clip(255.0 * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))]

class ImageHistogramsSelfNode:
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

    def generate(self, image: torch.Tensor, histogram_type="RGB Histogram Filled", histogram_size="medium", prompt=None, extra_pnginfo=None):
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

        return {
            "ui": save_result["ui"],
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

    def generate_histogram_template(self, image, colors, dpi):
        plt.figure()
        for i, col in enumerate(colors):
            histr = cv.calcHist([image], [i], None, [256], [0, 256])
            plt.plot(histr, color=col)
        plt.xlim([0, 256])
        plt.axis('off')
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close()
        buf.seek(0)
        return Image.open(buf)

    def generate_filled_histogram(self, image, dpi):
        color = ('b', 'g', 'r')
        plt.figure()
        for i, col in enumerate(color):
            histr = cv.calcHist([image], [i], None, [256], [0, 256])
            plt.plot(histr, color=col)
            plt.fill_between(range(256), histr[:, 0], color=col, alpha=0.5)
        plt.xlim([0, 256])
        buf = BytesIO()
        plt.axis('off')
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close()
        buf.seek(0)
        return Image.open(buf)

    def generate_line_histogram(self, image, dpi):
        return self.generate_histogram_template(image, ('b', 'g', 'r'), dpi)

    def generate_channel_histogram(self, image, channel, color, dpi):
        histr = cv.calcHist([image[:, :, channel]], [0], None, [256], [0, 256])
        plt.figure()
        plt.plot(histr, color=color)
        plt.fill_between(range(256), histr[:, 0], color=color, alpha=0.5)
        plt.xlim([0, 256])
        buf = BytesIO()
        plt.axis('off')
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close()
        buf.seek(0)
        return Image.open(buf)

    def generate_luminosity_histogram(self, image, dpi):
        luminosity = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
        plt.figure()
        histr = cv.calcHist([luminosity], [0], None, [256], [0, 256])
        plt.plot(histr, color='gray')
        plt.fill_between(range(256), histr[:, 0], color='gray', alpha=0.5)
        plt.xlim([0, 256])
        buf = BytesIO()
        plt.axis('off')
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close()
        buf.seek(0)
        return Image.open(buf)

## end
