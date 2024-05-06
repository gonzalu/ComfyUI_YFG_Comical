"""
@author: YFG
@title: YFG Meme Generator
@nickname: YFG Meme Generator
@description: This extension overlays a simple text string over an image and outputs the composited result.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch

class MemeGeneratorNode:

    _font_sizes = ["small", "medium", "large"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_in": ("IMAGE", {}),
                "text": ("STRING", {"default": "Change Meme"}),
                "font_size": (cls._font_sizes, {"default": "medium"},)  # Add choices for font_size
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image_out",)
    FUNCTION = "generate_meme"
    CATEGORY = "YFG"

    def generate_meme(self, image_in, text, font_size):
        # Convert tensor to numpy array and then to PIL Image
        image_tensor = image_in
        image_np = image_tensor.cpu().numpy()  # Change from CxHxW to HxWxC for Pillow
        
        # Convert float [0,1] tensor to uint8 image
        image = Image.fromarray((image_np.squeeze() * 255).astype(np.uint8))

        # Load font
        if font_size == "small":
            font = ImageFont.truetype(font="arial.ttf", size=15)
        elif font_size == "medium":
            font = ImageFont.truetype(font="arial.ttf", size=30)
        else:  # large
            font = ImageFont.truetype(font="arial.ttf", size=45)

        # Prepare to draw on image
        draw = ImageDraw.Draw(image)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_position = ((image.width - text_width) / 2, (image.height - text_height) / 2)

        # Draw the text
        draw.text(text_position, text, fill="black", font=font)

        # Convert back to Tensor if needed
        image_out = torch.tensor(np.array(image).astype(np.float32) / 255.0)  # Convert back to CxHxW
        image_out = torch.unsqueeze(image_out, 0)

        return (image_out,)
