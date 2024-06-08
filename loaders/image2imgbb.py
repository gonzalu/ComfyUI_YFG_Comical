"""
@app_author: YFG
@app_title: YFG Image to imgBB
@app_nickname: 🐯 YFG Image to imgBB
@app_description: This node loads an image, optionally uploads it to imgbb, and returns the image along with the image URL and API results.
"""
import io
import torch
import os
import sys
import json
import requests
import numpy as np
from PIL import Image, ImageOps, ImageSequence
from io import BytesIO

# Ensure the comfy directory is in the system path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

from comfy.cli_args import args
import folder_paths
import node_helpers

class Image2ImgBB:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "image": (["None"] + sorted(files), {"image_upload": True}),
                "upload_to_imgbb": ("BOOLEAN", {"default": False, "description": "Upload to imgBB?"})
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "MASK", "Image URL", "API Response")
    FUNCTION = "process_image"
    CATEGORY = "🐯 YFG/🔄 Loaders"
    FRIENDLY_NAME = "Image to imgBB"

    def process_image(self, image, upload_to_imgbb, **kwargs):
        graph_metadata = kwargs.get('graph_metadata', {})
        img_url = graph_metadata.get('image_url', '')

        output_image, output_mask, api_results = None, None, "No API call made"
        image_url = img_url

        # Attempt to load the image
        if image != "None":
            try:
                image_path = folder_paths.get_annotated_filepath(image)
                output_image, output_mask = self.load_local_image(image_path)
                api_results = f"Loaded local image: {image}"
            except (FileNotFoundError, ValueError) as e:
                print(f"Local image loading failed: {e}")

        # If local image loading failed, try to use the URL
        if output_image is None and img_url:
            if self.is_valid_url(img_url):
                try:
                    print(f"Loading image from URL: {img_url}")
                    output_image, output_mask = self.load_image_from_url(img_url)
                    api_results = f"Using image from URL: {img_url}"
                except Exception as e:
                    print(f"Failed to load image from URL: {e}")
                    api_results = f"Failed to load image from URL: {img_url}"
            else:
                print(f"Invalid URL: {img_url}")
                api_results = f"Invalid URL: {img_url}"

        # Upload the image to imgBB if required
        if upload_to_imgbb and output_image is not None:
            try:
                api_results = self.upload_to_imgbb_binary(image_path)
                api_response_json = json.loads(api_results)
                img_url = api_response_json.get('data', {}).get('url', '')
                if img_url:
                    graph_metadata['image_url'] = img_url
                    kwargs['graph_metadata'] = graph_metadata
                    image_url = img_url
                    print(f"Image uploaded to imgBB, URL saved: {img_url}")
            except Exception as e:
                print(f"Failed to upload image to imgBB: {e}")
                api_results = f"Failed to upload image to imgBB: {e}"

        print("API Response:", api_results)
        return output_image, output_mask, image_url, api_results

    def load_local_image(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Local image file not found: {image_path}")

        img = node_helpers.pillow(Image.open, image_path)
        output_images, output_masks = [], []
        w, h = None, None

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                raise ValueError("Image size mismatch")

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return output_image, output_mask

    def load_image_from_url(self, url):
        response = requests.get(url, stream=True)
        response.raise_for_status()
        img = node_helpers.pillow(Image.open(BytesIO(response.content)))

        output_images, output_masks = [], []
        w, h = None, None

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                raise ValueError("Image size mismatch")

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return output_image, output_mask

    def upload_to_imgbb_binary(self, image_path):
        api_key_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "imgbb_api_key.json")

        try:
            with open(api_key_path, "r") as key_file:
                api_key = json.load(key_file)["api_key"]
        except FileNotFoundError as fnf_error:
            print(f"File not found: {fnf_error}")
            return f"Error: {fnf_error}"
        except json.JSONDecodeError as json_error:
            print(f"Error decoding JSON: {json_error}")
            return f"Error: {json_error}"
        except Exception as e:
            print(f"Unexpected error: {e}")
            return f"Error: {e}"

        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        url = "https://api.imgbb.com/1/upload"
        files = {"image": (os.path.basename(image_path), image_data)}
        payload = {
            "key": api_key,
        }

        try:
            response = requests.post(url, files=files, data=payload)
            response.raise_for_status()
            result = response.json()
            print("API Response:", json.dumps(result, indent=2))
            return json.dumps(result, indent=2)
        except requests.exceptions.RequestException as e:
            print(f"Error uploading image: {e}")
            return f"Error uploading image: {e}"

    def is_valid_url(self, url):
        return url.startswith('http://') or url.startswith('https://')

    @classmethod
    def IS_CHANGED(cls, image):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not folder_paths.exists_annotated_filepath(image):
            return f"Invalid image file: {image}"
        return True
