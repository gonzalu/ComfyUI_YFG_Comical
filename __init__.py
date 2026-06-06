"""
@author: Manny Gonzalez
@title: 🐯 YFG Comical Nodes
@nickname: 🐯 YFG Comical Nodes
@description: Utility custom nodes for special effects, image manipulation and quality of life tools.
"""

from .image2histograms import ImageHistogramsNode
from .image2histogramscompact import ImageHistogramsNodeCompact
from .image2halftone import ImageHalftoneNode
from .images2sidebyside import ImagesSideBySideNode
from .switchers.imageSwitchers import *
from .loaders.image2imgbb import Image2ImgBB
from .loaders.imgbbLoader import *
from .loaders.smartcheckpointloader import SmartCheckpointLoader
from .image2contrastmask import ImageToContrastMask
from .VAEDecodePreview import VAEDecodePreview
from .MonoClip import MonoClip
from .pixelart import PixelArt
from .textMaskOverlay import TextMaskOverlay
from .RandomOrg import RandomOrgTrueRandomNumber
from .RandomOrgV2 import RandomOrgV2TrueRandomNumber
from .RandomImageFromDirectory import RandomImageFromDirectory
from .yfg_display_value import YFG_DisplayValue
from .YFGRandomPromptFromFile import YFGRandomPromptFromFile
from .civitai_metasave import YFG_CivitAI_MetaSave

NODE_CLASS_MAPPINGS = {
    "image_histograms_node": ImageHistogramsNode,
    "image_histograms_node_compact": ImageHistogramsNodeCompact,
    "image_halftone": ImageHalftoneNode,
    "images_side_by_side": ImagesSideBySideNode,
    "Image3Switcher_node": Image3SwitcherNode,
    "Image5Switcher_node": Image5SwitcherNode,
    "Image10Switcher_node": Image10SwitcherNode,
    "Image15Switcher_node": Image15SwitcherNode,
    "Image20Switcher_node": Image20SwitcherNode,
    "image2imbgg_node": Image2ImgBB,
    "imgbbLoader_node": ImgbbLoader,
    "storeURL_node": storeURL,
    "smartCheckpointLoader_node": SmartCheckpointLoader,
    "image2contrastMask_node": ImageToContrastMask,
    "VAEDecodePreview_node": VAEDecodePreview,
    "MonoClip_node": MonoClip,
    "PixelArt_node": PixelArt,
    "textMaskOverlay_node": TextMaskOverlay,
    "RandomOrgTrueRandomNumber_node": RandomOrgTrueRandomNumber,
    "RandomOrgV2TrueRandomNumber_node": RandomOrgV2TrueRandomNumber,
    "RandomImageFromDirectory_node": RandomImageFromDirectory,
    "YFG_DisplayValue": YFG_DisplayValue,
    "YFGRandomPromptFromFile_node": YFGRandomPromptFromFile,
    "YFG_CivitAI_MetaSave": YFG_CivitAI_MetaSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "image_histograms_node": "\U0001f42f YFG Histograms Generator",
    "image_histograms_node_compact": "\U0001f42f YFG Histograms Generator (compact)",
    "image_halftone": "\U0001f42f YFG Image Halftone Generator",
    "images_side_by_side": "\U0001f42f YFG Image Side by Side",
    "Image3Switcher_node": "\U0001f42f YFG 3 Image Switcher",
    "Image5Switcher_node": "\U0001f42f YFG 5 Image Switcher",
    "Image10Switcher_node": "\U0001f42f YFG 10 Image Switcher",
    "Image15Switcher_node": "\U0001f42f YFG 15 Image Switcher",
    "Image20Switcher_node": "\U0001f42f YFG 20 Image Switcher",
    "image2imbgg_node": "\U0001f42f YFG Image to imgBB",
    "imgbbLoader_node": "\U0001f42f YFG imgBB to Image",
    "storeURL_node": "\U0001f42f YFG Store URL",
    "smartCheckpointLoader_node": "\U0001f42f YFG Smart Checkpoint Loader",
    "image2contrastMask_node": "\U0001f42f YFG Image To Contrast Mask",
    "VAEDecodePreview_node": "\U0001f42f YFG VAE Decode with Preview",
    "MonoClip_node": "\U0001f42f YFG Monochrome Image Clip",
    "PixelArt_node": "\U0001f42f YFG PixelArt",
    "textMaskOverlay_node": "\U0001f42f YFG Text Mask Overlay",
    "RandomOrgTrueRandomNumber_node": "\U0001f42f YFG Random.org True Random Number",
    "RandomOrgV2TrueRandomNumber_node": "\U0001f42f YFG Random.org True Random Number (V2)",
    "RandomImageFromDirectory_node": "\U0001f42f YFG Random Image From Directory",
    "YFG_DisplayValue": "\U0001f42f YFG Display Value",
    "YFGRandomPromptFromFile_node": "\U0001f42f YFG Random Prompt From File",
    "YFG_CivitAI_MetaSave": "\U0001f42f YFG CivitAI MetaSave",
}

WEB_DIRECTORY = "./web"
print("------------------+-------------------")
print(f"\033[1;32m[YFG Comical]: 🐯 \033[93m\033[3m Loaded {len(NODE_CLASS_MAPPINGS)} nodes.\033[0m 🐯")
print("------------------+-------------------")
