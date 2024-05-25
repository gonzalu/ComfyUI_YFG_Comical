"""
@author: YFG
@title: YFG Histograms
@nickname: 🐯 YFG Halftone
@description: This node generates a halftone image from the input image.
"""

## Based on original code by Phil Gyford https://github.com/philgyford/python-halftone and ComfyUI node by aimingfail https://civitai.com/models/143293/image2halftone-node-for-comfyui ##

import folder_paths
import torch
import numpy as np
import os
import random
import json
from PIL import Image, ImageDraw, ImageOps, ImageStat, PngImagePlugin
from typing import List, Union
from io import BytesIO
from comfy.cli_args import args
from math import ceil, sqrt

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class ImageHalftoneNode:
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
                "samples": ("INT", {"default": 10, "min": 1, "max": 32}),
                "scaling": ("INT", {"default": 1, "min": 1, "max": 5}),
                "grayscale": (["No", "Yes"], {"default":"No"}),
                "angle_c": ("INT", {"default": 0, "min": 0, "max": 90}),
                "angle_m": ("INT", {"default": 15, "min": 0, "max": 90}),
                "angle_y": ("INT", {"default": 30, "min": 0, "max": 90}),
                "angle_k": ("INT", {"default": 45, "min": 0, "max": 90}),
                "preview": ("BOOLEAN", {"default": True}),
                "display": (["halftone", "original"], {"default": "halftone"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("Halftone", "Original Image")
    FUNCTION = "make_halftone"
    CATEGORY = "🐯 YFG"

    def make_halftone(self, image, samples, scaling, grayscale, angle_c, angle_m, angle_y, angle_k, preview, display, prompt=None, extra_pnginfo=None):
        tmpangles = [angle_c, angle_m, angle_y, angle_k]

        original_image = tensor2pil(image)
        halftone_image = self.make(sample=samples, scale=scaling, antialias=True, style="color" if grayscale == "No" else "grayscale", angles=tmpangles, imagePil=original_image)
        
        if not preview:
            return (pil2tensor(halftone_image), pil2tensor(original_image))
        
        ui_images = []
        if display == "original":
            original_image_filename = self.save_image(original_image, "original_image.png", prompt, extra_pnginfo)
            ui_images.append({"filename": original_image_filename, "type": self.type, "subfolder": self.output_dir})
        else:
            halftone_image_filename = self.save_image(halftone_image, "halftone_image.png", prompt, extra_pnginfo)
            ui_images.append({"filename": halftone_image_filename, "type": self.type, "subfolder": self.output_dir})
        
        return {
            "ui": {"images": ui_images},
            "result": (pil2tensor(halftone_image), pil2tensor(original_image)),
        }

    def make(self, sample=10, scale=1, percentage=0, filename_addition="_halftoned", angles=[0, 15, 30, 45], style="color", antialias=True, output_format="default", output_quality=95, save_channels=False, save_channels_format="default", save_channels_style="color", imagePil=None):
        if style == "grayscale":
            angles = angles[:1]
            gray_im = imagePil.convert("L")
            channel_images = self.halftone(imagePil, gray_im, sample, scale, angles, antialias)
            new = channel_images[0]
            new = new.convert("RGB")
        else:
            cmyk = self.gcr(imagePil, percentage)
            channel_images = self.halftone(imagePil, cmyk, sample, scale, angles, antialias)
            new = Image.merge("CMYK", channel_images)
            new = new.convert("RGB")
        return new

    def gcr(self, imagePil, percentage):
        cmyk_im = imagePil.convert("CMYK")
        if not percentage:
            return cmyk_im
        cmyk_im = cmyk_im.split()
        cmyk = [channel.load() for channel in cmyk_im]
        for x in range(imagePil.size[0]):
            for y in range(imagePil.size[1]):
                gray = int(min(cmyk[0][x, y], cmyk[1][x, y], cmyk[2][x, y]) * percentage / 100)
                for i in range(3):
                    cmyk[i][x, y] = cmyk[i][x, y] - gray
                cmyk[3][x, y] = gray
        return Image.merge("CMYK", cmyk_im)

    def halftone(self, imagePil, cmyk, sample, scale, angles, antialias):
        antialias_scale = 4
        if antialias:
            scale *= antialias_scale
        cmyk = cmyk.split()
        dots = []
        for channel, angle in zip(cmyk, angles):
            channel = channel.rotate(angle, expand=1)
            size = channel.size[0] * scale, channel.size[1] * scale
            half_tone = Image.new("L", size)
            draw = ImageDraw.Draw(half_tone)
            for x in range(0, channel.size[0], sample):
                for y in range(0, channel.size[1], sample):
                    box = channel.crop((x, y, x + sample, y + sample))
                    mean = ImageStat.Stat(box).mean[0]
                    diameter = (mean / 255) ** 0.5
                    box_size = sample * scale
                    draw_diameter = diameter * box_size
                    box_x, box_y = (x * scale), (y * scale)
                    x1 = box_x + ((box_size - draw_diameter) / 2)
                    y1 = box_y + ((box_size - draw_diameter) / 2)
                    x2 = x1 + draw_diameter
                    y2 = y1 + draw_diameter
                    draw.ellipse([(x1, y1), (x2, y2)], fill=255)
            half_tone = half_tone.rotate(-angle, expand=1)
            width_half, height_half = half_tone.size
            xx1 = (width_half - imagePil.size[0] * scale) / 2
            yy1 = (height_half - imagePil.size[1] * scale) / 2
            xx2 = xx1 + imagePil.size[0] * scale
            yy2 = yy1 + imagePil.size[1] * scale
            half_tone = half_tone.crop((xx1, yy1, xx2, yy2))
            if antialias:
                w, h = int((xx2 - xx1) / antialias_scale), int((yy2 - yy1) / antialias_scale)
                half_tone = half_tone.resize((w, h), resample=Image.LANCZOS)
            dots.append(half_tone)
        return dots

    def save_image(self, image, filename, prompt=None, extra_pnginfo=None):
        # Ensure the directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        file_path = os.path.join(self.output_dir, self.prefix_append + filename)
        metadata = PngImagePlugin.PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
        image.save(file_path, pnginfo=metadata, compress_level=self.compress_level)
        return file_path
