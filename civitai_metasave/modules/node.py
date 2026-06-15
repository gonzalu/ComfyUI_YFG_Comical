# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Save Image With CivitAI Metadata
# Nickname    : YFG_CivitAI_MetaSave
# Description : A single ComfyUI output node that saves images in PNG, JPEG,
#               or WebP format while embedding A1111-compatible metadata
#               (parameters, model/LoRA/embedding hashes, seed, sampler, etc.)
#               so that CivitAI automatically recognizes and displays the
#               generation info, resources, and prompts.
#
#               Replaces the two-node design (SaveImageWithMetaData +
#               CreateExtraMetaData) from the upstream
#               comfyui_image_metadata_extension repo with a single node that
#               includes four optional custom key/value extra-metadata pairs
#               directly on its input panel.
#
#               Compatible with classic SD, KSampler, KSamplerAdvanced, Flux,
#               SD3, Ideogram, SamplerCustomAdvanced, and LoRA workflows.
#
# Fix (2026-06-15): results[subfolder] now uses os.path.relpath() so the
#               ComfyUI /view? URL receives a proper relative subfolder
#               instead of the full absolute Windows path, which was causing
#               Chromium-based browsers (Chrome, Edge) to produce malformed
#               drag-and-drop source URLs.
# =============================================================================

import json
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np
import piexif
import piexif.helper
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths

from . import hook
from .capture import Capture
from .trace import Trace
from .utils.log import print_warning


# ---------------------------------------------------------------------------
# Enums for the node's dropdown inputs
# ---------------------------------------------------------------------------

class OutputFormat(str, Enum):
    PNG          = "png"
    PNG_JSON     = "png_with_json"
    JPG          = "jpg"
    JPG_JSON     = "jpg_with_json"
    WEBP         = "webp"
    WEBP_JSON    = "webp_with_json"


class QualityOption(str, Enum):
    MAX    = "max"
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class MetadataScope(str, Enum):
    FULL            = "full"
    DEFAULT         = "default"
    PARAMETERS_ONLY = "parameters_only"
    WORKFLOW_ONLY   = "workflow_only"
    NONE            = "none"


# ---------------------------------------------------------------------------
# YFG_CivitAI_MetaSave  (single unified node)
# ---------------------------------------------------------------------------

class YFG_CivitAI_MetaSave:
    """
    Saves images with full A1111-compatible CivitAI metadata embedded.

    Drop-in replacement for the two-node SaveImageWithMetaData /
    CreateExtraMetaData combo.  The four optional extra key/value pairs are
    built directly into this node so no helper node is required.
    """

    OUTPUT_FORMATS   = [e.value for e in OutputFormat]
    QUALITY_OPTIONS  = [e.value for e in QualityOption]
    METADATA_OPTIONS = [e.value for e in MetadataScope]
    NEEDS_METADATA_KEYS = {"seed", "width", "height", "pprompt", "nprompt", "model"}

    def __init__(self):
        self.output_dir     = folder_paths.get_output_directory()
        self.type           = "output"
        self.prefix_append  = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {
                    "tooltip": "The images to save."
                }),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI",
                    "tooltip": (
                        "Prefix for the saved filename. Supports tokens: "
                        "%date:yyyy-MM-dd%, %seed%, %pprompt:32%, %nprompt:32%, "
                        "%model%, %width%, %height%."
                    ),
                }),
                "subdirectory_name": ("STRING", {
                    "default": "",
                    "tooltip": (
                        "Optional sub-folder inside the output directory. "
                        "Supports %date:yyyy-MM-dd% tokens. Leave blank for the default output folder."
                    ),
                }),
                "output_format": (cls.OUTPUT_FORMATS, {
                    "default": "png_with_json",
                    "tooltip": (
                        "Image format to save. The *_with_json variants also write a "
                        "sidecar .json file containing the raw workflow."
                    ),
                }),
                "quality": (cls.QUALITY_OPTIONS, {
                    "default": "max",
                    "tooltip": (
                        "Output quality: max=100 (lossless WebP), high=80, medium=60, low=30. "
                        "Ignored for PNG."
                    ),
                }),
                "metadata_scope": (cls.METADATA_OPTIONS, {
                    "default": "full",
                    "tooltip": (
                        "full            – A1111 parameters + full ComfyUI workflow\n"
                        "default         – same as the built-in SaveImage node\n"
                        "parameters_only – A1111-style parameters string only\n"
                        "workflow_only   – ComfyUI workflow JSON only\n"
                        "none            – no metadata embedded"
                    ),
                }),
                "include_batch_num": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Append a 5-digit batch index to the filename when saving multiple images.",
                }),
                "prefer_nearest": ("BOOLEAN", {
                    "default": True,
                    "tooltip": (
                        "When multiple upstream nodes provide the same field, "
                        "prefer the one closest (fewest hops) to this node."
                    ),
                }),
            },
            "optional": {
                # Extra custom metadata key/value pairs baked directly into the node
                "extra_key1":   ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata key 1"}),
                "extra_value1": ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata value 1"}),
                "extra_key2":   ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata key 2"}),
                "extra_value2": ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata value 2"}),
                "extra_key3":   ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata key 3"}),
                "extra_value3": ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata value 3"}),
                "extra_key4":   ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata key 4"}),
                "extra_value4": ("STRING", {"default": "", "multiline": False, "tooltip": "Custom metadata value 4"}),
            },
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION     = "save_images"
    OUTPUT_NODE  = True
    CATEGORY     = "YFG"
    DESCRIPTION  = (
        "Saves images with full A1111-compatible CivitAI metadata (model, LoRA, "
        "embedding hashes, sampler settings, prompts) so CivitAI automatically "
        "populates resources and generation info. Supports PNG, JPEG, and WebP. "
        "Replaces the two-node SaveImageWithMetaData + CreateExtraMetaData combo."
    )

    # -----------------------------------------------------------------------
    # Filename tokeniser
    # -----------------------------------------------------------------------

    _pattern_format = re.compile(r"(%[^%]+%)")

    @classmethod
    def _parse_placeholders(cls, filename):
        return re.findall(cls._pattern_format, filename) if "%" in filename else []

    def _needs_pnginfo_for_filename(self, segments):
        for seg in segments:
            key = seg.strip("%").split(":")[0]
            if key in self.NEEDS_METADATA_KEYS:
                return True
        return False

    @classmethod
    def _format_filename(cls, filename, pnginfo_dict, segments=None):
        if "%" not in filename:
            return filename

        segments = segments or re.findall(cls._pattern_format, filename)
        now = datetime.now()
        date_table = {
            "yyyy": f"{now.year}",
            "MM":   f"{now.month:02d}",
            "dd":   f"{now.day:02d}",
            "hh":   f"{now.hour:02d}",
            "mm":   f"{now.minute:02d}",
            "ss":   f"{now.second:02d}",
        }
        pnginfo_dict = pnginfo_dict or {}

        for seg in segments:
            parts = seg.strip("%").split(":")
            key   = parts[0]

            if key == "seed":
                seed = pnginfo_dict.get("Seed")
                if seed is None:
                    print_warning("Seed not found in pnginfo_dict!")
                filename = filename.replace(seg, str(seed or ""))

            elif key in {"width", "height"}:
                size = pnginfo_dict.get("Size", "x").split("x")
                if "Size" not in pnginfo_dict:
                    print_warning("Size not found in pnginfo_dict!")
                value = size[0] if key == "width" else size[1]
                filename = filename.replace(seg, value)

            elif key in {"pprompt", "nprompt"}:
                prompt_key = "Positive prompt" if key == "pprompt" else "Negative prompt"
                text       = pnginfo_dict.get(prompt_key, "").replace("\n", " ")
                if not text:
                    print_warning(f"{prompt_key} not found in pnginfo_dict!")
                length   = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                filename = filename.replace(seg, (text[:length].strip() if length else text.strip()))

            elif key == "model":
                model  = pnginfo_dict.get("Model", "")
                model  = os.path.splitext(os.path.basename(model))[0]
                length = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                filename = filename.replace(seg, model[:length] if length else model)

            elif key == "date":
                date_fmt = parts[1] if len(parts) > 1 else "yyyyMMddhhmmss"
                for k, v in date_table.items():
                    date_fmt = date_fmt.replace(k, v)
                filename = filename.replace(seg, date_fmt)

        return filename

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _parse_output_format(self, output_format):
        fmt = OutputFormat(output_format)
        save_json  = fmt.name.endswith("JSON")
        base_fmt   = fmt.value.replace("_with_json", "")
        return base_fmt, save_json

    def _get_quality_value(self, quality):
        return {
            QualityOption.MAX:    100,
            QualityOption.HIGH:   80,
            QualityOption.MEDIUM: 60,
            QualityOption.LOW:    30,
        }.get(QualityOption(quality), 100)

    def _find_next_available_filename(self, folder, name, ext):
        existing = {f.stem for f in Path(folder).glob(f"{name}_*.{ext}")}
        i = 1
        while f"{name}_{i:05d}" in existing:
            i += 1
        return i

    def _build_extra_metadata(self, **kwargs):
        """Collect the four optional key/value pairs from node inputs."""
        extra = {}
        for i in range(1, 5):
            key   = kwargs.get(f"extra_key{i}",   "").strip()
            value = kwargs.get(f"extra_value{i}", "").strip()
            if key:
                extra[key] = value
            elif value:
                raise ValueError(
                    f"extra_value{i} has a value ('{value}') but extra_key{i} is empty. "
                    f"Please provide a key for this metadata entry."
                )
        return extra

    # -----------------------------------------------------------------------
    # Core: pnginfo assembly
    # -----------------------------------------------------------------------

    def _prepare_pnginfo(self, pnginfo_obj, pnginfo_dict, batch_number, total_images,
                         prompt, extra_pnginfo, metadata_scope, extra_metadata):
        """
        Build and return a PngInfo object with all requested metadata layers.
        Returns None when metadata_scope is 'none'.
        """
        scope = MetadataScope(metadata_scope)

        if scope == MetadataScope.NONE:
            return None

        if pnginfo_dict:
            pnginfo_copy = pnginfo_dict.copy()

            if total_images > 1:
                pnginfo_copy["Batch index"] = batch_number
                pnginfo_copy["Batch size"]  = total_images

            if scope in (MetadataScope.FULL, MetadataScope.PARAMETERS_ONLY):
                parameters = Capture.gen_parameters_str(pnginfo_copy)
                if parameters and "Steps" in parameters:
                    pnginfo_obj.add_text("parameters", parameters)
                    if scope == MetadataScope.PARAMETERS_ONLY:
                        # Add user extra metadata then stop
                        for k, v in extra_metadata.items():
                            pnginfo_obj.add_text(k, v)
                        return pnginfo_obj

        if prompt is not None and scope != MetadataScope.WORKFLOW_ONLY:
            pnginfo_obj.add_text("prompt", json.dumps(prompt))

        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                pnginfo_obj.add_text(x, json.dumps(extra_pnginfo[x]))

        # Extra user-supplied key/value pairs always go in last
        for k, v in extra_metadata.items():
            pnginfo_obj.add_text(k, v)

        return pnginfo_obj

    @classmethod
    def _gen_pnginfo(cls, prompt, prefer_nearest):
        inputs = Capture.get_inputs()
        trace_from_save   = Trace.trace(hook.current_save_image_node_id, prompt)
        inputs_before_save = Trace.filter_inputs_by_trace_tree(inputs, trace_from_save, prefer_nearest)

        sampler_id = Trace.find_sampler_node_id(trace_from_save)
        if sampler_id:
            trace_from_sampler    = Trace.trace(sampler_id, prompt)
            inputs_before_sampler = Trace.filter_inputs_by_trace_tree(inputs, trace_from_sampler, prefer_nearest)
        else:
            inputs_before_sampler = {}

        return Capture.gen_pnginfo_dict(inputs_before_sampler, inputs_before_save, prompt)

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def save_images(
        self,
        images,
        filename_prefix     = "ComfyUI",
        subdirectory_name   = "",
        output_format       = "png_with_json",
        quality             = "max",
        metadata_scope      = "full",
        include_batch_num   = False,
        prefer_nearest      = True,
        prompt              = None,
        extra_pnginfo       = None,
        extra_key1   = "", extra_value1 = "",
        extra_key2   = "", extra_value2 = "",
        extra_key3   = "", extra_value3 = "",
        extra_key4   = "", extra_value4 = "",
    ):
        # Build the optional extra-metadata dict from the inline key/value pairs
        extra_metadata = self._build_extra_metadata(
            extra_key1=extra_key1, extra_value1=extra_value1,
            extra_key2=extra_key2, extra_value2=extra_value2,
            extra_key3=extra_key3, extra_value3=extra_value3,
            extra_key4=extra_key4, extra_value4=extra_value4,
        )

        base_format, save_workflow_json = self._parse_output_format(output_format)
        pnginfo_obj = PngInfo()

        # Resolve filename tokens
        filename_prefix   = filename_prefix.strip()
        subdirectory_name = subdirectory_name.strip()
        segments          = self._parse_placeholders(filename_prefix)

        scope = MetadataScope(metadata_scope)
        pnginfo_dict = None
        if scope in (MetadataScope.FULL, MetadataScope.PARAMETERS_ONLY) \
                or self._needs_pnginfo_for_filename(segments):
            pnginfo_dict = self._gen_pnginfo(prompt, prefer_nearest)

        filename_prefix   = self._format_filename(filename_prefix, pnginfo_dict, segments) + self.prefix_append
        subdirectory_name = self._format_filename(subdirectory_name, pnginfo_dict)

        # Determine output folder.
        # get_save_image_path() handles the slash in filename_prefix as a subfolder
        # automatically and returns a correct relative `subfolder` string.
        image_shape = images[0].shape
        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, image_shape[1], image_shape[0]
            )

        # If a separate subdirectory_name was supplied, override the folder
        # and recompute the relative subfolder for the /view? URL.
        if subdirectory_name:
            full_output_folder = os.path.join(self.output_dir, subdirectory_name)
            subfolder          = subdirectory_name
            filename           = filename_prefix

        os.makedirs(full_output_folder, exist_ok=True)

        results       = []
        images_length = len(images)
        last_filename = None

        for batch_number, image in enumerate(images):
            i   = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            # Build metadata for this image
            metadata = self._prepare_pnginfo(
                pnginfo_obj, pnginfo_dict, batch_number, images_length,
                prompt, extra_pnginfo, metadata_scope, extra_metadata
            )

            # Resolve filename (collision handling)
            if include_batch_num:
                file = f"{filename}_{batch_number:05d}.{base_format}"
            else:
                file = f"{filename}.{base_format}"

            path = os.path.join(full_output_folder, file)
            if os.path.exists(path):
                count = self._find_next_available_filename(full_output_folder, filename, base_format)
                file  = f"{filename}_{count:05d}.{base_format}"
                path  = os.path.join(full_output_folder, file)

            last_filename = file
            quality_value = self._get_quality_value(quality)

            # Save image
            if base_format == "webp":
                img.save(path, "WEBP", lossless=(quality_value == 100), quality=quality_value)
            elif base_format == "png":
                img.save(path, pnginfo=metadata, compress_level=self.compress_level)
            else:  # jpg
                img.save(path, optimize=True, quality=quality_value)

            # Embed EXIF for jpg / webp (CivitAI reads this too)
            if base_format in ("jpg", "webp") and pnginfo_dict:
                exif_bytes = piexif.dump({
                    "Exif": {
                        piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(
                            Capture.gen_parameters_str(pnginfo_dict), encoding="unicode"
                        )
                    }
                })
                piexif.insert(exif_bytes, path)

            # FIX: use the relative `subfolder` string, not the absolute
            # full_output_folder path. ComfyUI's /view? endpoint expects a
            # path relative to the output directory, and passing an absolute
            # Windows path was producing malformed URLs that Chromium-based
            # browsers (Chrome, Edge) rejected for drag-and-drop operations.
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type":     self.type,
            })

        # Optionally save sidecar workflow JSON
        if save_workflow_json and images_length > 0 and last_filename and extra_pnginfo:
            json_file = os.path.join(
                full_output_folder,
                last_filename.replace(f".{base_format}", ".json")
            )
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(extra_pnginfo.get("workflow", {}), f)

        return {"ui": {"images": results}}
