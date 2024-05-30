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
        font = ImageFont.truetype("seguisb.ttf", font_size)  # Arial font
    except IOError:
        font = ImageFont.load_default()

    text = f"*NO INPUT IMAGE {input_number}*"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    text_position = ((1024 - text_width) // 2, (1024 - text_height) // 2)
    draw.text(text_position, text, fill=(255, 69, 0), font=font)  # Neutral red color for the font
    
    return pil2tensor(image)

def draw_rounded_rectangle(draw, bbox, radius, fill):
    draw.rounded_rectangle(bbox, radius=3, fill=fill, outline=None)

def generate_routing_diagram(selected_input, num_inputs):
    rect_height = 60  # Height for each input rectangle
    padding = 20  # Padding between rectangles
    diagram_height = num_inputs * (rect_height + padding) + padding  # Total height of the diagram
    image = Image.new("RGB", (1024, diagram_height), (255, 255, 255))  # Dynamic height based on inputs
    draw = ImageDraw.Draw(image)
    font_size = 30  # Adjusted font size to small
    circle_radius = 8  # Reduced size of circles
    try:
        font = ImageFont.truetype("seguisb.ttf", font_size)  # Arial font
    except IOError:
        font = ImageFont.load_default()

    input_labels = [f"Image {i+1}" for i in range(num_inputs)]
    output_label = "Output"
    
    # Calculate the width and height for the rectangles based on the largest label "Image 20"
    max_label = "Image 20"
    text_bbox = draw.textbbox((0, 0), max_label, font=font)
    max_text_width = text_bbox[2] - text_bbox[0]
    max_text_height = text_bbox[3] - text_bbox[1]
    rect_width = max_text_width + 2 * padding

    input_y_positions = [padding + i * (rect_height + padding) + rect_height // 2 for i in range(num_inputs)]
    output_y_position = diagram_height // 2

    # Drawing background gradient
    top_color = (220, 255, 220)  # #dcffdc
    bottom_color = (230, 255, 230)  # #e6ffe6
    for y in range(diagram_height // 2):
        ratio = y / (diagram_height // 2)
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, (diagram_height // 2) - y), (1024, (diagram_height // 2) - y)], fill=(r, g, b))
        draw.line([(0, (diagram_height // 2) + y), (1024, (diagram_height // 2) + y)], fill=(r, g, b))

    # Draw input labels and circles
    for i, label in enumerate(input_labels):
        rect_bbox = (10, input_y_positions[i] - rect_height // 2, 10 + rect_width, input_y_positions[i] + rect_height // 2)
        draw_rounded_rectangle(draw, rect_bbox, 10, "#afebff")
        
        # Center the text vertically
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_height = text_bbox[3] - text_bbox[1]
        ascent, descent = font.getmetrics()
        text_position = (20, input_y_positions[i] - (text_height + descent) // 2)
        draw.text(text_position, label, fill="#404040", font=font)
        
        # Draw circle on the right edge of the input rectangle
        circle_x = 10 + rect_width
        circle_y = input_y_positions[i]
        draw.ellipse((circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius), fill="#7f0000")

    # Draw output label and circle
    rect_bbox = (1024 - 10 - rect_width, output_y_position - rect_height // 2, 1024 - 10, output_y_position + rect_height // 2)
    draw_rounded_rectangle(draw, rect_bbox, 10, "#afebff")
    
    # Center the text vertically
    text_bbox = draw.textbbox((0, 0), output_label, font=font)
    text_height = text_bbox[3] - text_bbox[1]
    ascent, descent = font.getmetrics()
    text_position = (1024 - 10 - padding - max_text_width, output_y_position - (text_height + descent) // 2)
    draw.text(text_position, output_label, fill="#404040", font=font)
    
    # Draw circle on the left edge of the output rectangle
    circle_x = 1024 - 10 - rect_width
    circle_y = output_y_position
    draw.ellipse((circle_x - circle_radius, circle_y - circle_radius, circle_x + circle_radius, circle_y + circle_radius), fill="#7f0000")

    if selected_input in input_labels:
        input_index = input_labels.index(selected_input)
        input_position = input_y_positions[input_index]

        # Calculate positions for the line
        start_x = 10 + rect_width  # Edge of the input rectangle
        start_y = input_position
        end_x = 1024 - 10 - rect_width  # Edge of the output rectangle
        end_y = output_y_position

        # Draw line and arrowhead
        line_color = "#7f0000"
        line_width = 10
        arrow_head_length = 25

        # Draw the line in a single pass
        line_points = [
            (start_x, start_y), 
            (start_x + 75, start_y), 
            (end_x - 75 - arrow_head_length, end_y),  # Ending 75px before the arrowhead
            (end_x - arrow_head_length, end_y)  # End at the back of the arrowhead
        ]
        draw.line(line_points, width=line_width, fill=line_color, joint="curve")

        # Draw the arrowhead touching the left edge of the output rectangle
        arrow_head = [(end_x - arrow_head_length, end_y - circle_radius), (end_x - arrow_head_length, end_y + circle_radius), (end_x, end_y)]
        draw.polygon(arrow_head, fill=line_color)

    return pil2tensor(image)

class BaseImageSwitcherNode:
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("Selected Image", "Connection Diagram")
    CATEGORY = "🐯 YFG/🔀 Switchers"
    FUNCTION = "select_image"

    def __init__(self, num_inputs):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5))
        self.compress_level = 1
        self.num_inputs = num_inputs

    @classmethod
    def INPUT_TYPES(cls, num_inputs):
        return {
            "required": {
                "selected_image": ([f"Image {i+1}" for i in range(num_inputs)], {"default": "Image 1"}),
                "font_size": (["Small", "Medium", "Large"], {"default": "Medium"}),
                "font_color": (["White", "Black", "Red", "Green", "Blue", "Yellow", "Brown", "Orange"], {"default": "White"}),
                "font_file": ("STRING", {"default": "seguisb.ttf"}),  # Arial font
                "image_label": ("BOOLEAN", {"default": True}),
                "preview": ("BOOLEAN", {"default": True}),
                "preview_type": (["Input Image", "Connection Diagram"], {"default": "Input Image"}),
            },
            "optional": {f"Image {i+1}": ("IMAGE",) for i in range(num_inputs)},
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    def select_image(self, **inputs):
        images = [inputs.get(f"Image {i+1}", None) for i in range(self.num_inputs)]
        for i, img in enumerate(images):
            if img is None:
                images[i] = generate_placeholder_image(i+1)

        selected_image = inputs["selected_image"]
        preview_type = inputs["preview_type"]
        font_size = inputs["font_size"]
        font_color = inputs["font_color"]
        font_file = inputs["font_file"]
        image_label = inputs["image_label"]
        preview = inputs["preview"]
        prompt = inputs.get("prompt")
        extra_pnginfo = inputs.get("extra_pnginfo")

        selected_index = int(selected_image.split()[1]) - 1
        selected_pil_image = tensor2pil(images[selected_index])
        selected_tensor = images[selected_index]
        label = selected_image

        connection_diagram_tensor = generate_routing_diagram(selected_image, self.num_inputs)
        connection_diagram_pil = tensor2pil(connection_diagram_tensor)

        if preview and image_label and preview_type == "Input Image":
            self.add_label(selected_pil_image, label, font_file, font_size, font_color)

        if preview_type == "Connection Diagram":
            preview_pil_image = connection_diagram_pil
        else:
            preview_pil_image = selected_pil_image

        if not preview:
            return (selected_tensor, connection_diagram_tensor)

        ui_images = []
        preview_image_filename = self.save_image(preview_pil_image, "preview_image.png", prompt, extra_pnginfo)
        ui_images.append({"filename": preview_image_filename, "type": self.type, "subfolder": self.output_dir})

        return {
            "ui": {"images": ui_images},
            "result": (selected_tensor, connection_diagram_tensor),
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

class Image3SwitcherNode(BaseImageSwitcherNode):
    def __init__(self):
        super().__init__(num_inputs=3)

    @classmethod
    def INPUT_TYPES(cls):
        return super().INPUT_TYPES(3)

class Image5SwitcherNode(BaseImageSwitcherNode):
    def __init__(self):
        super().__init__(num_inputs=5)

    @classmethod
    def INPUT_TYPES(cls):
        return super().INPUT_TYPES(5)

class Image10SwitcherNode(BaseImageSwitcherNode):
    def __init__(self):
        super().__init__(num_inputs=10)

    @classmethod
    def INPUT_TYPES(cls):
        return super().INPUT_TYPES(10)

class Image15SwitcherNode(BaseImageSwitcherNode):
    def __init__(self):
        super().__init__(num_inputs=15)

    @classmethod
    def INPUT_TYPES(cls):
        return super().INPUT_TYPES(15)

class Image20SwitcherNode(BaseImageSwitcherNode):
    def __init__(self):
        super().__init__(num_inputs=20)

    @classmethod
    def INPUT_TYPES(cls):
        return super().INPUT_TYPES(20)
