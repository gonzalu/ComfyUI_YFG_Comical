"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
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

class ImagesSideBySideNode:
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "mode": (["Split", "Side-by-Side"], {"default": "Split"}),
                "display": (["Side-by-Side", "Image 1", "Image 2"], {"default": "Side-by-Side"}),
                "font_size": (["Small", "Medium", "Large"], {"default": "Medium"}),
                "font_color": (["White", "Black", "Red", "Green", "Blue", "Yellow", "Brown", "Orange"], {"default": "White"}),
                "font_file": ("STRING", {"default": "micross.ttf"}),                
                "image_label": ("BOOLEAN", {"default": True}),
                "preview": ("BOOLEAN", {"default": True}),                
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Combined Image",)
    FUNCTION = "combine_images"
    CATEGORY = "🐯 YFG"

    def combine_images(self, image1, image2, mode, preview, display, font_file, font_size, font_color, image_label, prompt=None, extra_pnginfo=None):
        pil_image1 = tensor2pil(image1)
        pil_image2 = tensor2pil(image2)

        if mode == "Split":
            combined_image = self.make_split(pil_image1, pil_image2, font_file, font_size, font_color, image_label)
        else:
            combined_image = self.make_side_by_side(pil_image1, pil_image2, font_file, font_size, font_color, image_label)
        
        if not preview:
            return (pil2tensor(combined_image),)
        
        ui_images = []
        if display == "Image 1":
            image1_filename = self.save_image(pil_image1, "image1.png", prompt, extra_pnginfo)
            ui_images.append({"filename": image1_filename, "type": self.type, "subfolder": self.output_dir})
        elif display == "Image 2":
            image2_filename = self.save_image(pil_image2, "image2.png", prompt, extra_pnginfo)
            ui_images.append({"filename": image2_filename, "type": self.type, "subfolder": self.output_dir})
        else:
            combined_image_filename = self.save_image(combined_image, "combined_image.png", prompt, extra_pnginfo)
            ui_images.append({"filename": combined_image_filename, "type": self.type, "subfolder": self.output_dir})
        
        return {
            "ui": {"images": ui_images},
            "result": (pil2tensor(combined_image),),
        }

    def make_side_by_side(self, image1, image2, font_file, font_size, font_color, image_label):
        width1, height1 = image1.size
        width2, height2 = image2.size
        total_width = width1 + width2
        max_height = max(height1, height2)

        new_image = Image.new("RGB", (total_width, max_height))
        new_image.paste(image1, (0, 0))
        new_image.paste(image2, (width1, 0))

        separator_x = width1
        third_height = max_height // 3

        # Draw the white line
        draw = ImageDraw.Draw(new_image)
        draw.line([(separator_x, 0), (separator_x, third_height)], fill="white", width=3)
        draw.line([(separator_x, 2 * third_height), (separator_x, max_height)], fill="white", width=3)
        draw.line([(separator_x, third_height), (separator_x, 2 * third_height)], fill="white", width=10)

        # Draw the black outline
        self.draw_outline(draw, separator_x, 0, third_height, 3)
        self.draw_outline(draw, separator_x, 2 * third_height, max_height, 3)
        self.draw_outline(draw, separator_x, third_height, 2 * third_height, 10)

        if image_label:
            self.add_labels(draw, width1, width2, max_height, "Image 1", "Image 2", font_file, font_size, font_color)

        return new_image

    def make_split(self, image1, image2, font_file, font_size, font_color, image_label):
        width1, height1 = image1.size
        width2, height2 = image2.size
        half_width1 = width1 // 2
        half_width2 = width2 // 2
        max_height = max(height1, height2)

        new_image = Image.new("RGB", (half_width1 + half_width2, max_height))

        left_half = image1.crop((0, 0, half_width1, height1))
        right_half = image2.crop((width2 - half_width2, 0, width2, height2))

        new_image.paste(left_half, (0, 0))
        new_image.paste(right_half, (half_width1, 0))

        separator_x = half_width1
        third_height = max_height // 3

        # Draw the white line
        draw = ImageDraw.Draw(new_image)
        draw.line([(separator_x, 0), (separator_x, third_height)], fill="white", width=3)
        draw.line([(separator_x, 2 * third_height), (separator_x, max_height)], fill="white", width=3)
        draw.line([(separator_x, third_height), (separator_x, 2 * third_height)], fill="white", width=10)

        # Draw the black outline
        self.draw_outline(draw, separator_x, 0, third_height, 3)
        self.draw_outline(draw, separator_x, 2 * third_height, max_height, 3)
        self.draw_outline(draw, separator_x, third_height, 2 * third_height, 10)

        if image_label:
            self.add_labels(draw, half_width1, half_width2, max_height, "Image 1", "Image 2", font_file, font_size, font_color)

        return new_image

    def draw_outline(self, draw, x, y1, y2, width):
        # Draw the white line
        draw.line([(x, y1), (x, y2)], fill="white", width=width)

        # Draw the black outline around the line
        draw.line([(x - width // 2, y1), (x - width // 2, y2)], fill="black", width=1)
        draw.line([(x + width // 2, y1), (x + width // 2, y2)], fill="black", width=1)

    def add_labels(self, draw, width1, width2, max_height, text1, text2, font_file, font_size, font_color):
        font_size_value = self.get_font_size(font_size, max_height)
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

        text1_bbox = draw.textbbox((0, 0), text1, font=font)
        text2_bbox = draw.textbbox((0, 0), text2, font=font)
        text1_width = text1_bbox[2] - text1_bbox[0]
        text2_width = text2_bbox[2] - text2_bbox[0]

        self.draw_text_with_outline(draw, (width1 // 2 - text1_width // 2, 10), text1, font, font_color_rgb, "black")
        self.draw_text_with_outline(draw, (width1 + width2 // 2 - text2_width // 2, 10), text2, font, font_color_rgb, "black")

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
