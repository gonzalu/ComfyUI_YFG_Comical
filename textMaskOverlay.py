"""
@author: YFG
@title: Text Mask Overlay
@nickname: 🐱 Text Mask Overlay
@description: This extension overlays text onto a mask using specified fonts. It allows dynamic font selection from system fonts, a specific node folder, or a user-defined directory.
"""
import cv2
import numpy as np
import math
import torch
from PIL import Image, ImageDraw, ImageFont
import os
import platform

class TextMaskOverlay:
    @classmethod
    def INPUT_TYPES(cls):
        font_sources = ["System", "Node Folder", "Directory"]

        # Default user directory to fonts
        user_directory = os.path.expandvars("%LocalAppData%\\Microsoft\\Windows\\Fonts")

        # Define font lists for different sources
        system_fonts = cls.get_font_list("System")
        node_fonts = cls.get_font_list("Node Folder")
        directory_fonts = cls.get_font_list("Directory", user_directory)

        if not system_fonts:
            print("Error: No system fonts found.")
            system_fonts = ["No system fonts available"]
        if not node_fonts:
            print("Error: No fonts found in the YFG node folder.")
            node_fonts = ["No fonts available in YFG folder"]
        if not directory_fonts:
            print(f"Error: No fonts found in directory '{user_directory}' or the directory does not exist.")
            directory_fonts = ["No fonts available in specified directory"]

        return {
            "required": {
                "font_source": (font_sources,),
                "system_font": (system_fonts, {"default": "impact.ttf"}),
                "node_font": (node_fonts, {"default": "malgunbd.ttf"}),
                "usr_font_dir": ("STRING", {"default": user_directory, "multiline": False}),
                "directory_font": (directory_fonts, {"default": directory_fonts[0] if directory_fonts else ""}),
                "text": ("STRING", {"default": "TEXT", "multiline": False}),
                'mask': ("MASK",),
            },
        }

    CATEGORY = "🐯 YFG"
    RETURN_TYPES = ("MASK", "IMAGE")
    RETURN_NAMES = ("mask", "image")
    FUNCTION = "process_mask"
    OUTPUT_NODE = True    

    def process_mask(self, mask, font_source, system_font, node_font, usr_font_dir, directory_font, text):
        # Process the mask with text overlay
        processed_mask = self.apply_text_mask(mask, font_source, system_font, node_font, usr_font_dir, directory_font, text)
        # Convert the modified mask to an image
        image = self.mask_to_image(processed_mask)
        return processed_mask, image

    def apply_text_mask(self, mask, font_source, system_font, node_font, usr_font_dir, directory_font, text):
        if len(mask.shape) > 2:
            mask = mask[0]
        mask = (mask.numpy() * 255).astype('uint8')

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            tmp = np.zeros_like(mask)

            rows = min(max(round(h / w), 1), 3)
            row_num = math.ceil(len(text) / rows)
            font_size = math.floor(w / row_num)
            dx = round(w - font_size * row_num, 1)
            dy = round((h - font_size * rows) / 2 / rows, 1)

            print(rows, row_num, font_size)

            # Select font based on source
            if font_source == "System":
                font = self.get_font("System", "", system_font, font_size)
            elif font_source == "Node Folder":
                font = self.get_font("Node Folder", "", node_font, font_size)
            elif font_source == "Directory":
                font = self.get_font("Directory", usr_font_dir, directory_font, font_size)

            image2 = Image.fromarray(tmp)
            draw = ImageDraw.Draw(image2)
            for row in range(rows):
                draw.text((x + dx, y + (font_size + dy * 2) * row + dy - font_size / 5),
                          text[row_num * row:row_num * (row + 1)], font=font, fill='white')

        else:
            image2 = Image.fromarray(np.zeros_like(mask))

        return torch.from_numpy((np.array(image2).astype('float32') / 255))

    def mask_to_image(self, mask):
        """
        Converts a modified mask to an RGB image format.
        """
        # Using the provided method for mask conversion
        result = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3)
        return result

    def get_font(self, font_source, usr_font_dir, font_name, size):
        """
        Loads a font based on the selected source and specified filename.
        """
        font_path = None

        if font_source == "System":
            font_path = self.find_system_font(font_name)
        elif font_source == "Node Folder":
            font_path = self.find_node_font(font_name)
        elif font_source == "Directory":
            font_path = os.path.join(usr_font_dir, font_name)
            if not os.path.exists(usr_font_dir):
                print(f"Error: The directory '{usr_font_dir}' does not exist.")
                return self.get_default_system_font(size)
        
        if font_path and os.path.isfile(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
            except IOError:
                print(f"Font '{font_name}' at '{font_path}' not found. Using default system font 'impact.ttf'.")
                font = self.get_default_system_font(size)
        else:
            print(f"Font path '{font_path}' not valid or does not exist. Using default system font 'impact.ttf'.")
            font = self.get_default_system_font(size)

        return font

    def find_system_font(self, font_name):
        """
        Finds the specified font in the system's font directory.
        """
        font_dir = self.get_system_font_dir()
        return os.path.join(font_dir, font_name) if font_dir else None

    def find_node_font(self, font_name):
        """
        Finds the specified font in the node's predefined font directory.
        """
        yfg_font_dir = self.get_node_font_dir()
        return os.path.join(yfg_font_dir, font_name)

    def get_default_system_font(self, size):
        """
        Loads a common system font if available. Defaults to a basic bitmap font if not found.
        """
        try:
            font = ImageFont.truetype("impact.ttf", size)
        except IOError:
            print("System font 'impact.ttf' not found. Using default bitmap font.")
            font = ImageFont.load_default()
        
        return font

    @classmethod
    def get_font_list(cls, source, directory=""):
        """
        Gets the list of fonts based on the selected source.
        """
        font_list = []
        if source == "System":
            font_dir = cls.get_system_font_dir()
        elif source == "Node Folder":
            font_dir = cls.get_node_font_dir()
        elif source == "Directory":
            font_dir = directory

        if font_dir and os.path.exists(font_dir):
            font_list = [f for f in os.listdir(font_dir) if os.path.isfile(os.path.join(font_dir, f)) and f.lower().endswith(".ttf")]
            if not font_list:
                print(f"Error: No fonts found in '{font_dir}'.")
        else:
            print(f"Error: The directory '{font_dir}' does not exist.")

        return font_list

    @classmethod
    def get_system_font_dir(cls):
        """
        Returns the system font directory based on the OS.
        """
        if platform.system() == "Windows":
            system_root = os.environ.get("SystemRoot")
            return os.path.join(system_root, "Fonts") if system_root else None
        elif platform.system() == "Linux":
            return "/usr/share/fonts/truetype"
        elif platform.system() == "Darwin":
            return "/System/Library/Fonts"
        else:
            return None

    @classmethod
    def get_node_font_dir(cls):
        """
        Returns the node's font directory relative to the current file.
        """
        node_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(node_dir, "fonts")

