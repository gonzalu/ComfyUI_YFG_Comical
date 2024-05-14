"""
@author: YFG
@title: YFG Histograms
@nickname: YFG Histograms
@description: This extension calculates the histogram of an image and outputs the results as graph images for individual channels as well as RGB and Luminosity.
"""
from math import ceil, sqrt

import torch
import numpy as np

from ..inc.histogram import *

class ImageHistograms_v2(ImageHistogramUtils):
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
    CATEGORY = "YFG"

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

## end