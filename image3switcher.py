"""
@author: YFG
@title: YFG Image 3 Switcher
@nickname: 🐯 YFG Image 3 Switcher
@description: This node allows the user to select between three images and outputs the selected image.
"""

import folder_paths
import torch
import numpy as np
import os
import random
import json
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from typing import List, Union
from comfy.cli_args import args

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def generate_placeholder_image(input_number):
    image = Image.new("RGB", (1024, 1024), (54, 69, 79))  # Dark charcoal gray background
    draw = ImageDraw.Draw(image)
    font_size = 50
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)  # Heavy narrow display font (Arial Bold as a substitute)
    except IOError:
        font = ImageFont.load_default()

    text = f"*NO INPUT IMAGE {input_number}*"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    text_position = ((1024 - text_width) // 2, (1024 - text_height) // 2)
    draw.text(text_position, text, fill=(255, 69, 0), font=font)  # Neutral red color for the font
    
    return pil2tensor(image)

class Image3SwitcherNode:
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "selected_image": (["Image 1", "Image 2", "Image 3"], {"default": "Image 1"}),
                "font_size": (["Small", "Medium", "Large"], {"default": "Medium"}),
                "font_color": (["White", "Black", "Red", "Green", "Blue", "Yellow", "Brown", "Orange"], {"default": "White"}),
                "font_file": ("STRING", {"default": "micross.ttf"}),
                "image_label": ("BOOLEAN", {"default": True}),
                "preview": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "Image 1": ("IMAGE",),
                "Image 2": ("IMAGE",),
                "Image 3": ("IMAGE",),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Selected Image",)
    FUNCTION = "select_image"
    CATEGORY = "🐯 YFG"

    def select_image(self, **inputs):
        image1 = inputs.get("Image 1", None)
        if image1 is None:
            image1 = generate_placeholder_image(1)

        image2 = inputs.get("Image 2", None)
        if image2 is None:
            image2 = generate_placeholder_image(2)

        image3 = inputs.get("Image 3", None)
        if image3 is None:
            image3 = generate_placeholder_image(3)

        selected_image = inputs["selected_image"]
        font_size = inputs["font_size"]
        font_color = inputs["font_color"]
        font_file = inputs["font_file"]
        image_label = inputs["image_label"]
        preview = inputs["preview"]
        prompt = inputs.get("prompt")
        extra_pnginfo = inputs.get("extra_pnginfo")

        if selected_image == "Image 1":
            selected_pil_image = tensor2pil(image1)
            selected_tensor = image1
            label = "Image 1"
        elif selected_image == "Image 2":
            selected_pil_image = tensor2pil(image2)
            selected_tensor = image2
            label = "Image 2"
        else:
            selected_pil_image = tensor2pil(image3)
            selected_tensor = image3
            label = "Image 3"

        if preview and image_label:
            self.add_label(selected_pil_image, label, font_file, font_size, font_color)

        if not preview:
            return (selected_tensor,)

        ui_images = []
        selected_image_filename = self.save_image(selected_pil_image, "selected_image.png", prompt, extra_pnginfo)
        ui_images.append({"filename": selected_image_filename, "type": self.type, "subfolder": self.output_dir})

        return {
            "ui": {"images": ui_images},
            "result": (selected_tensor,),
        }

    def add_label(self, image, label, font_file, font_size, font_color):
        draw = ImageDraw.Draw(image)
        font_size_value = self.get_font_size(font_size, image.height)
        try:
            font = ImageFont.truetype(font_file, font_size_value)
        except IOError:
            font = ImageFont.load_default()

        font_color_rgb = {
            "White": (255, 255, 255),
            "Black": (0, 0, 0),
            "Red": (255, 0, 0),
            "Green": (0, 255, 0),
            "Blue": (0, 0, 255),
            "Yellow": (255, 255, 0),
            "Brown": (165, 42, 42),
            "Orange": (255, 165, 0)
        }[font_color]

        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]

        self.draw_text_with_outline(draw, (image.width // 2 - text_width // 2, 10), label, font, font_color_rgb, "black")

    def draw_text_with_outline(self, draw, position, text, font, fill_color, outline_color):
        x, y = position
        # Draw outline
        draw.text((x - 1, y - 1), text, font=font, fill=outline_color)
        draw.text((x + 1, y - 1), text, font=font, fill=outline_color)
        draw.text((x - 1, y + 1), text, font=font, fill=outline_color)
        draw.text((x + 1, y + 1), text, font=font, fill=outline_color)
        # Draw text
        draw.text(position, text, font=font, fill=fill_color)

    def get_font_size(self, font_size, max_height):
        if font_size == "Small":
            return max_height // 30
        elif font_size == "Large":
            return max_height // 10
        else:  # "Medium"
            return max_height // 20

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
