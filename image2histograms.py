"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
"""
from math import ceil, sqrt
import torch
from PIL import Image
import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt
from io import BytesIO
from typing import List, Union

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

class ImageHistogramsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "histogram_size": (["small", "medium", "large"], {"default": "medium"}),
            },
        }

    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("Original Image", "RGB Histogram Filled", "RGB Histogram Lines", "Red Channel", "Green Channel", "Blue Channel", "Luminosity")
    CATEGORY = "🐯 YFG"

    def generate(self, image: torch.Tensor, histogram_size="medium"):
        if image.size(0) == 0:
            return (torch.zeros(0),)

        original_image = tensor2pil(image)  # Directly pass through the original image

        # Set histogram resolution based on the input size
        dpi = {'small': 50, 'medium': 100, 'large': 150}.get(histogram_size, 100)

        # Prepare histograms
        image_array = np.array(original_image[0])
        histogram_filled = self.generate_filled_histogram(image_array, dpi)
        histogram_lines = self.generate_line_histogram(image_array, dpi)
        red_hist = self.generate_channel_histogram(image_array, 2, 'red', dpi)
        green_hist = self.generate_channel_histogram(image_array, 1, 'green', dpi)
        blue_hist = self.generate_channel_histogram(image_array, 0, 'blue', dpi)
        lum_hist = self.generate_luminosity_histogram(image_array, dpi)

        return (pil2tensor(original_image), pil2tensor([histogram_filled]), pil2tensor([histogram_lines]), pil2tensor([red_hist]), pil2tensor([green_hist]), pil2tensor([blue_hist]), pil2tensor([lum_hist]))

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