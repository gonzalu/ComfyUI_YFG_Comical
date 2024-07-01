"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
"""

## Based on original code by XSS https://civitai.com/models/24869?modelVersionId=47776 ##

import torch
import nodes
import folder_paths
import comfy.sd

class VAEDecodePreview():
    def __init__(self, device="cpu"):
        self.device = device
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                    "samples": ("LATENT", ),
                    "vae": ("VAE", )
                }
            }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "decode_preview"
    OUTPUT_NODE = True
    CATEGORY = "🐯 YFG"

    def decode_preview(self, vae, samples):
        images = vae.decode(samples["samples"])
        saveImages = nodes.SaveImage()
        saveImages.output_dir = folder_paths.get_temp_directory()
        saveImages.type = "temp"
        results = saveImages.save_images(images)
        results["result"] = (images, )
        return results
