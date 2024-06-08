"""
@app_author: YFG
@app_title: YFG Image Loader from imgBB
@app_nickname: 🐯 YFG imgBB Loader
@app_description: This node loads an image from a provided URL and outputs the image and mask.
"""
import io
import torch
import requests
import numpy as np
from PIL import Image, ImageOps, ImageSequence
from io import BytesIO
import os
import folder_paths
import comfy.utils
from typing import List, Dict, Tuple

from comfy.cli_args import args

import sys

# Ensure the comfy directory is in the system path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

def tensor2pil(image: torch.Tensor, mode=None):
    return numpy2pil(image.cpu().numpy().squeeze(), mode=mode)

def pil2numpy(image: Image.Image):
    return np.array(image).astype(np.float32) / 255.0

def numpy2pil(image: np.ndarray, mode=None):
    return Image.fromarray(np.clip(255.0 * image, 0, 255).astype(np.uint8), mode)

def prepare_image_for_preview(image: Image.Image, output_dir: str, prefix=None):
    if prefix is None:
        prefix = "preview_" + "".join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))

    # Save image to temp folder
    (
        outdir,
        filename,
        counter,
        subfolder,
        _,
    ) = folder_paths.get_save_image_path(prefix, output_dir, image.width, image.height)
    file = f"{filename}_{counter:05}_.png"
    image.save(os.path.join(outdir, file), format="PNG", compress_level=4)

    return {
        "filename": file,
        "subfolder": subfolder,
        "type": "temp",
    }

def load_images_from_url(urls: List[str], keep_alpha_channel=False):
    images = []
    masks = []

    for url in urls:
        if url.startswith("data:image/"):
            i = Image.open(io.BytesIO(base64.b64decode(url.split(",")[1])))
        elif url.startswith("file://"):
            url = url[7:]
            if not os.path.isfile(url):
                raise Exception(f"File {url} does not exist")

            i = Image.open(url)
        elif url.startswith("http://") or url.startswith("https://"):
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                raise Exception(response.text)

            i = Image.open(io.BytesIO(response.content))
        elif url.startswith("/view?"):
            from urllib.parse import parse_qs

            qs = parse_qs(url[6:])
            filename = qs.get("name", qs.get("filename", None))
            if filename is None:
                raise Exception(f"Invalid url: {url}")

            filename = filename[0]
            subfolder = qs.get("subfolder", None)
            if subfolder is not None:
                filename = os.path.join(subfolder[0], filename)

            dirtype = qs.get("type", ["input"])
            if dirtype[0] == "input":
                url = os.path.join(folder_paths.get_input_directory(), filename)
            elif dirtype[0] == "output":
                url = os.path.join(folder_paths.get_output_directory(), filename)
            elif dirtype[0] == "temp":
                url = os.path.join(folder_paths.get_temp_directory(), filename)
            else:
                raise Exception(f"Invalid url: {url}")

            i = Image.open(url)
        elif url == "":
            continue
        else:
            url = folder_paths.get_annotated_filepath(url)
            if not os.path.isfile(url):
                raise Exception(f"Invalid url: {url}")

            i = Image.open(url)

        i = ImageOps.exif_transpose(i)
        has_alpha = "A" in i.getbands()
        mask = None

        if "RGB" not in i.mode:
            i = i.convert("RGBA") if has_alpha else i.convert("RGB")

        if has_alpha:
            mask = i.getchannel("A")

            # Recreate image to fix weird RGB image
            alpha = i.split()[-1]
            image = Image.new("RGB", i.size, (0, 0, 0))
            image.paste(i, mask=alpha)
            image.putalpha(alpha)

            if not keep_alpha_channel:
                image = image.convert("RGB")
        else:
            image = i

        images.append(image)
        masks.append(mask)

    return (images, masks)
    
class ImgbbLoader:
    def __init__(self) -> None:
        self.output_dir = folder_paths.get_temp_directory()
        self.filename_prefix = "TempImageFromUrl"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": False}),
            },
            "optional": {
                "keep_alpha_channel": (
                    "BOOLEAN",
                    {"default": False, "label_on": "enabled", "label_off": "disabled"},
                ),
                "output_mode": (
                    "BOOLEAN",
                    {"default": False, "label_on": "list", "label_off": "batch"},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "BOOLEAN")
    OUTPUT_IS_LIST = (True, True, False)
    RETURN_NAMES = ("images", "masks", "has_image")
    CATEGORY = "🐯 YFG/🔄 Loaders"
    FUNCTION = "load_image_from_url"

    def load_image_from_url(self, url="", keep_alpha_channel=False, output_mode=False, **kwargs):
        if not url:
            raise ValueError("No URL provided for image loading")

        urls = url.strip().split("\n")
        images, masks = load_images_from_url(urls, keep_alpha_channel)
        if len(images) == 0:
            image = torch.zeros((1, 64, 64, 3), dtype=torch.float32, device="cpu")
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
            return ([image], [mask], False)

        previews = []
        np_images = []
        np_masks = []

        for image, mask in zip(images, masks):
            # Save image to temp folder
            preview = prepare_image_for_preview(image, self.output_dir, self.filename_prefix)
            image_tensor = self.pil2tensor(image)

            if mask:
                mask_tensor = np.array(mask).astype(np.float32) / 255.0
                mask_tensor = 1.0 - torch.from_numpy(mask_tensor)
            else:
                mask_tensor = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

            previews.append(preview)
            np_images.append(image_tensor)
            np_masks.append(mask_tensor.unsqueeze(0))

        if output_mode:
            result = (np_images, np_masks, True)
        else:
            has_size_mismatch = False
            if len(np_images) > 1:
                for image in np_images[1:]:
                    if image.shape[1] != np_images[0].shape[1] or image.shape[2] != np_images[0].shape[2]:
                        has_size_mismatch = True
                        break

            if has_size_mismatch:
                raise Exception("To output as batch, images must have the same size. Use list output mode instead.")

            result = ([torch.cat(np_images)], [torch.cat(np_masks)], True)

        return {"ui": {"images": previews}, "result": result}

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0)[None,]

    def is_valid_url(self, url):
        return url.startswith('http://') or url.startswith('https://')

class storeURL:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "getURL"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "🐯 YFG/Loaders"

    def getURL(self, text, unique_id=None, extra_pnginfo=None):
        if unique_id is not None and extra_pnginfo is not None:
            if not isinstance(extra_pnginfo, list):
                print("Error: extra_pnginfo is not a list")
            elif (
                not isinstance(extra_pnginfo[0], dict)
                or "workflow" not in extra_pnginfo[0]
            ):
                print("Error: extra_pnginfo[0] is not a dict or missing 'workflow' key")
            else:
                workflow = extra_pnginfo[0]["workflow"]
                node = next(
                    (x for x in workflow["nodes"] if str(x["id"]) == str(unique_id[0])),
                    None,
                )
                if node:
                    node["widgets_values"] = [text]

        return {"ui": {"text": text}, "result": (text,)}