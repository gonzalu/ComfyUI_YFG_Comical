# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave V2 - Save Image With CivitAI Metadata
# Nickname    : YFG_CivitAI_MetaSave_V2
# Description : Second-generation CivitAI metadata save node. Shares the whole
#               capture / trace / hashing pipeline with V1 but presents a clean
#               widget layout that V1 could not adopt without breaking saved
#               workflows.
#
#               Changes from V1:
#                 * output_format reduced to png / jpg / webp, with the sidecar
#                   workflow JSON promoted to its own boolean toggle
#                 * quality is a real 1-100 integer instead of four buckets
#                 * filename tokens can pull from the extra metadata fields and
#                   from any captured metadata field
#                 * file numbering is configurable (mode / start / padding), so
#                   the first file can be _00001 instead of unnumbered
#                 * extra metadata key/value pairs grow on demand and live at
#                   the very bottom of the node
#                 * returns filename and filepath as outputs
#
#               V1 remains available and unchanged for existing workflows.
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
# Enums
# ---------------------------------------------------------------------------

class OutputFormatV2(str, Enum):
    PNG  = "png"
    JPG  = "jpg"
    WEBP = "webp"


class MetadataScopeV2(str, Enum):
    FULL            = "full"
    DEFAULT         = "default"
    PARAMETERS_ONLY = "parameters_only"
    WORKFLOW_ONLY   = "workflow_only"
    NONE            = "none"


class NumberingMode(str, Enum):
    ON_CONFLICT = "on_conflict"
    ALWAYS      = "always"


# ---------------------------------------------------------------------------
# Flexible optional inputs
# ---------------------------------------------------------------------------

class FlexibleOptionalInputType(dict):
    """
    A dict subclass that reports containing *every* key, so ComfyUI accepts
    dynamically-created inputs that were never declared in INPUT_TYPES.

    This is what lets the extra metadata key/value pairs grow without bound:
    the frontend adds extra_key2 / extra_value2 / extra_key3 / ... and ComfyUI
    asks this dict whether those inputs exist. We answer yes and hand back the
    fallback type, and the values arrive in the node function's **kwargs.

    Entries passed in via *data* behave normally, keeping their declared
    defaults and tooltips.

    Credit: technique from rgthree-comfy (rgthree/rgthree-comfy), used there
    for Any Switch, Power Lora Loader and similar dynamic nodes.
    """

    def __init__(self, fallback_type, data: dict | None = None):
        super().__init__()
        self.fallback_type = fallback_type
        self.data = data or {}
        for k, v in self.data.items():
            self[k] = v

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        return (self.fallback_type, {"default": "", "multiline": False})

    def __contains__(self, key):
        return True


# ---------------------------------------------------------------------------
# YFG_CivitAI_MetaSave_V2
# ---------------------------------------------------------------------------

class YFG_CivitAI_MetaSave_V2:
    """
    Saves images with full A1111-compatible CivitAI metadata embedded, with a
    clean widget layout and an unbounded number of extra metadata fields.
    """

    OUTPUT_FORMATS   = [e.value for e in OutputFormatV2]
    METADATA_OPTIONS = [e.value for e in MetadataScopeV2]
    NUMBERING_MODES  = [e.value for e in NumberingMode]

    # Filename tokens that require the full metadata capture pass
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
                    "tooltip": "The images to save.",
                }),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI",
                    "tooltip": (
                        "Prefix for the saved filename.\n\n"
                        "Built-in tokens:\n"
                        "  %date:yyyy-MM-dd%  %seed%  %model%  %width%  %height%\n"
                        "  %pprompt:32%  %nprompt:32%   (:N truncates to N chars)\n\n"
                        "Custom metadata tokens:\n"
                        "  %extra:KEY%      value of the extra metadata field named KEY\n"
                        "  %extra:KEY:12%   same, truncated to 12 characters\n"
                        "  %KEY%            extra field KEY, or any captured metadata\n"
                        "                   field such as %Sampler%, %Steps%, %CFG scale%\n\n"
                        "Key matching is case-insensitive. Unresolved tokens are replaced "
                        "with nothing and logged to the console. A literal / creates a "
                        "subfolder; slashes inside substituted values are made safe."
                    ),
                }),
                "subdirectory_name": ("STRING", {
                    "default": "",
                    "tooltip": (
                        "Optional sub-folder inside the output directory. Supports the "
                        "same tokens as filename_prefix. Leave blank for the default "
                        "output folder."
                    ),
                }),
                "output_format": (cls.OUTPUT_FORMATS, {
                    "default": "png",
                    "tooltip": (
                        "Image format to save.\n"
                        "png  – lossless, metadata stored in a PNG text chunk\n"
                        "jpg  – lossy, metadata stored in EXIF UserComment\n"
                        "webp – metadata in EXIF; lossless when quality is 100"
                    ),
                }),
                "save_workflow_json": ("BOOLEAN", {
                    "default": False,
                    "tooltip": (
                        "Also write a sidecar .json file containing the raw ComfyUI "
                        "workflow alongside the image."
                    ),
                }),
                "quality": ("INT", {
                    "default": 100,
                    "min":     1,
                    "max":     100,
                    "tooltip": (
                        "Compression quality for jpg and webp. 100 is best quality "
                        "(and lossless for webp). Ignored for png."
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
                "filename_numbering": (cls.NUMBERING_MODES, {
                    "default": "always",
                    "tooltip": (
                        "always      – every file is numbered, including the first\n"
                        "on_conflict – first file is unnumbered; a number is only added "
                        "when the name already exists"
                    ),
                }),
                "numbering_start": ("INT", {
                    "default": 1,
                    "min":     0,
                    "max":     999999,
                    "tooltip": "First number to use. 0 starts at 0000, 1 starts at 0001.",
                }),
                "numbering_padding": ("INT", {
                    "default": 5,
                    "min":     1,
                    "max":     10,
                    "tooltip": "Digits to pad the number to. 5 gives 00001, 4 gives 0001.",
                }),
                "include_batch_num": ("BOOLEAN", {
                    "default": False,
                    "tooltip": (
                        "Append a 5-digit batch index to the filename when saving "
                        "multiple images from one run."
                    ),
                }),
                "prefer_nearest": ("BOOLEAN", {
                    "default": True,
                    "tooltip": (
                        "When multiple upstream nodes provide the same metadata field, "
                        "prefer the one closest (fewest graph hops) to this node."
                    ),
                }),
            },
            # Extra metadata pairs live at the bottom of the node. Only the
            # first pair is declared here; the frontend extension in
            # web/js/civitai_metasave_v2.js adds extra_key2 / extra_value2 and
            # beyond on demand, and they arrive in **kwargs.
            #
            # ComfyUI's native COMFY_AUTOGROW_V3 would remove the need for that
            # extension, but it is resolved during the socket pass of
            # addInputs(), which runs before the widget pass — so its groups
            # render above the node's ordinary widgets instead of below them.
            # Until that ordering is addressable, the extension gives the
            # correct layout and also grows on typing, not just on connecting.
            "optional": FlexibleOptionalInputType("STRING", {
                "extra_key1": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": (
                        "Metadata key, e.g. 'Prompt Index'. Also usable in "
                        "filename_prefix as %extra:Prompt Index%.\n\n"
                        "Fill this in and another pair appears below."
                    ),
                }),
                "extra_value1": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": (
                        "Metadata value. Type it, or wire it from another node — "
                        "numbers and strings are both accepted."
                    ),
                }),
            }),
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES    = ("STRING", "STRING")
    RETURN_NAMES    = ("filename", "filepath")
    OUTPUT_TOOLTIPS = (
        "Filename of the last image saved this run, including extension.",
        "Full absolute path of the last image saved this run.",
    )
    FUNCTION    = "save_images"
    OUTPUT_NODE = True
    CATEGORY    = "🐯 YFG/💾 Save"
    DESCRIPTION = (
        "Saves images with full A1111-compatible CivitAI metadata (model, LoRA, "
        "embedding hashes, sampler settings, prompts) so CivitAI automatically "
        "populates resources and generation info.\n\n"
        "V2 adds metadata-aware filename tokens, configurable file numbering, "
        "unlimited extra metadata fields that grow as you use them, and "
        "filename / filepath outputs."
    )

    # -----------------------------------------------------------------------
    # Filename tokeniser
    # -----------------------------------------------------------------------

    _pattern_format = re.compile(r"(%[^%]+%)")

    # Characters illegal in filenames on Windows and/or POSIX. Applied only to
    # substituted token VALUES, never the raw prefix, so a literal "/" typed
    # into filename_prefix still creates a subfolder.
    _ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    @classmethod
    def _parse_placeholders(cls, filename):
        return re.findall(cls._pattern_format, filename) if "%" in filename else []

    @classmethod
    def _sanitize_token_value(cls, value):
        """Make a substituted token value safe to embed in a filename."""
        s = str(value).replace("\n", " ").replace("\r", " ")
        s = cls._ILLEGAL_FILENAME_CHARS.sub("_", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s.strip(". ")          # trailing dots/spaces are invalid on Windows

    @staticmethod
    def _lookup_metadata_key(key, *sources):
        """Resolve a token key against dicts: exact match first, then case-insensitive."""
        for src in sources:
            if not src:
                continue
            if key in src:
                return src[key]
            lowered = {str(k).lower(): v for k, v in src.items()}
            if key.lower() in lowered:
                return lowered[key.lower()]
        return None

    def _needs_pnginfo_for_filename(self, segments, extra_metadata=None):
        """
        Whether the full metadata capture pass is needed to resolve the filename.
        Tokens satisfied by the extra fields alone, and %date%, do not need it.
        """
        extra_metadata = extra_metadata or {}
        for seg in segments:
            parts = seg.strip("%").split(":")
            key   = parts[0]

            if key == "date":
                continue
            if key in self.NEEDS_METADATA_KEYS:
                return True
            if key == "extra":
                continue
            if self._lookup_metadata_key(key, extra_metadata) is not None:
                continue
            return True
        return False

    @classmethod
    def _format_filename(cls, filename, pnginfo_dict, segments=None, extra_metadata=None):
        if "%" not in filename:
            return filename

        segments       = segments if segments is not None else cls._parse_placeholders(filename)
        extra_metadata = extra_metadata or {}
        pnginfo_dict   = pnginfo_dict or {}

        now = datetime.now()
        date_table = {
            "yyyy": f"{now.year}",
            "MM":   f"{now.month:02d}",
            "dd":   f"{now.day:02d}",
            "hh":   f"{now.hour:02d}",
            "mm":   f"{now.minute:02d}",
            "ss":   f"{now.second:02d}",
        }

        for seg in segments:
            parts = seg.strip("%").split(":")
            key   = parts[0]

            if key == "seed":
                seed = pnginfo_dict.get("Seed")
                if seed is None:
                    print_warning("Seed not found in metadata!")
                filename = filename.replace(seg, str(seed or ""))

            elif key in {"width", "height"}:
                size = pnginfo_dict.get("Size", "x").split("x")
                if "Size" not in pnginfo_dict:
                    print_warning("Size not found in metadata!")
                filename = filename.replace(seg, size[0] if key == "width" else size[1])

            elif key in {"pprompt", "nprompt"}:
                prompt_key = "Positive prompt" if key == "pprompt" else "Negative prompt"
                text       = pnginfo_dict.get(prompt_key, "")
                if not text:
                    print_warning(f"{prompt_key} not found in metadata!")
                text     = cls._sanitize_token_value(text)
                length   = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                filename = filename.replace(seg, text[:length].strip() if length else text)

            elif key == "model":
                model  = os.path.splitext(os.path.basename(pnginfo_dict.get("Model", "")))[0]
                model  = cls._sanitize_token_value(model)
                length = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                filename = filename.replace(seg, model[:length] if length else model)

            elif key == "date":
                date_fmt = parts[1] if len(parts) > 1 else "yyyyMMddhhmmss"
                for k, v in date_table.items():
                    date_fmt = date_fmt.replace(k, v)
                filename = filename.replace(seg, date_fmt)

            else:
                # %extra:KEY%  /  %extra:KEY:12%  /  %KEY%
                if key == "extra":
                    if len(parts) < 2:
                        print_warning("Filename token %extra% needs a key, e.g. %extra:Prompt Index%")
                        filename = filename.replace(seg, "")
                        continue
                    lookup_key = parts[1]
                    length     = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                    value      = cls._lookup_metadata_key(lookup_key, extra_metadata)
                    label      = f"%extra:{lookup_key}%"
                else:
                    lookup_key = key
                    length     = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                    value      = cls._lookup_metadata_key(lookup_key, extra_metadata, pnginfo_dict)
                    label      = f"%{lookup_key}%"

                if value is None:
                    print_warning(
                        f"Filename token {label} could not be resolved from the extra "
                        f"metadata fields or the image metadata; substituting nothing."
                    )
                    filename = filename.replace(seg, "")
                    continue

                text     = cls._sanitize_token_value(value)
                filename = filename.replace(seg, text[:length].strip() if length else text)

        return filename

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    # Matches extra_key1 (what the frontend extension creates) and also
    # extra.key0, the naming ComfyUI's native autogrow would produce. Both are
    # accepted so a hand-built prompt or a future switch to autogrow needs no
    # change here.
    _EXTRA_KEY_RE = re.compile(r"^extra([._])key(\d+)$")

    def _build_extra_metadata(self, values):
        """
        Collect every extra key/value pair present in *values*, returned in
        numeric order regardless of the order they arrive in. Handles gaps left
        by pairs the user cleared or disconnected.
        """
        found = {}
        for name, raw_key in values.items():
            match = self._EXTRA_KEY_RE.match(name)
            if not match:
                continue
            sep = match.group(1)
            n   = int(match.group(2))
            key = str(raw_key if raw_key is not None else "").strip()

            # Only None counts as absent. Using `or ""` here would silently
            # discard legitimate falsy values — most importantly an integer 0,
            # which is exactly what a prompt index or counter emits on its
            # first item.
            raw_value = values.get(f"extra{sep}value{n}")
            value     = "" if raw_value is None else str(raw_value).strip()

            if key:
                found[n] = (key, value)
            elif value:
                raise ValueError(
                    f"An extra metadata value ('{value}') was supplied with no key. "
                    f"Fill in the matching key field, or clear the value."
                )

        return {key: value for _, (key, value) in sorted(found.items())}

    def _next_available_number(self, folder, base, ext, start=1, padding=5):
        """
        Lowest unused integer >= start for files named "<base>_<number>.<ext>".

        Uses a directory listing rather than glob() because the base name can
        contain glob metacharacters such as [ ] * ? once prompt text has been
        substituted into it.
        """
        prefix = f"{base}_"
        suffix = f".{ext}"
        used   = set()

        try:
            entries = os.listdir(folder)
        except OSError:
            entries = []

        for entry in entries:
            if not entry.startswith(prefix) or not entry.endswith(suffix):
                continue
            tail = entry[len(prefix):-len(suffix)]
            if tail.isdigit():
                used.add(int(tail))

        n = max(0, int(start))
        while n in used:
            n += 1
        return n

    # -----------------------------------------------------------------------
    # Core: pnginfo assembly
    # -----------------------------------------------------------------------

    def _prepare_pnginfo(self, pnginfo_obj, pnginfo_dict, batch_number, total_images,
                         prompt, extra_pnginfo, metadata_scope, extra_metadata):
        """Build a PngInfo object for this image. Returns None when scope is 'none'."""
        scope = MetadataScopeV2(metadata_scope)

        if scope == MetadataScopeV2.NONE:
            return None

        if pnginfo_dict:
            pnginfo_copy = pnginfo_dict.copy()

            if total_images > 1:
                pnginfo_copy["Batch index"] = batch_number
                pnginfo_copy["Batch size"]  = total_images

            if scope in (MetadataScopeV2.FULL, MetadataScopeV2.PARAMETERS_ONLY):
                parameters = Capture.gen_parameters_str(pnginfo_copy)
                if parameters and "Steps" in parameters:
                    pnginfo_obj.add_text("parameters", parameters)
                    if scope == MetadataScopeV2.PARAMETERS_ONLY:
                        for k, v in extra_metadata.items():
                            pnginfo_obj.add_text(k, v)
                        return pnginfo_obj

        if prompt is not None and scope != MetadataScopeV2.WORKFLOW_ONLY:
            pnginfo_obj.add_text("prompt", json.dumps(prompt))

        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                pnginfo_obj.add_text(x, json.dumps(extra_pnginfo[x]))

        for k, v in extra_metadata.items():
            pnginfo_obj.add_text(k, v)

        return pnginfo_obj

    @classmethod
    def _gen_pnginfo(cls, prompt, prefer_nearest):
        inputs             = Capture.get_inputs()
        trace_from_save    = Trace.trace(hook.current_save_image_node_id, prompt)
        inputs_before_save = Trace.filter_inputs_by_trace_tree(inputs, trace_from_save, prefer_nearest)

        sampler_id = Trace.find_sampler_node_id(trace_from_save)
        if sampler_id:
            trace_from_sampler    = Trace.trace(sampler_id, prompt)
            inputs_before_sampler = Trace.filter_inputs_by_trace_tree(
                inputs, trace_from_sampler, prefer_nearest)
        else:
            inputs_before_sampler = {}

        return Capture.gen_pnginfo_dict(inputs_before_sampler, inputs_before_save, prompt)

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def save_images(
        self,
        images,
        filename_prefix    = "ComfyUI",
        subdirectory_name  = "",
        output_format      = "png",
        save_workflow_json = False,
        quality            = 100,
        metadata_scope     = "full",
        filename_numbering = "always",
        numbering_start    = 1,
        numbering_padding  = 5,
        include_batch_num  = False,
        prefer_nearest     = True,
        prompt             = None,
        extra_pnginfo      = None,
        extra_key1         = "",
        extra_value1       = "",
        **kwargs,
    ):
        # Merge the declared pair with any the frontend extension added
        # (extra_key2 / extra_value2 / ...), which arrive in kwargs.
        extra_inputs = {"extra_key1": extra_key1, "extra_value1": extra_value1}
        extra_inputs.update({
            k: v for k, v in kwargs.items() if k.startswith("extra")
        })
        extra_metadata = self._build_extra_metadata(extra_inputs)

        base_format = OutputFormatV2(output_format).value
        pnginfo_obj = PngInfo()

        # Resolve filename tokens
        filename_prefix   = filename_prefix.strip()
        subdirectory_name = subdirectory_name.strip()
        segments          = self._parse_placeholders(filename_prefix)
        sub_segments      = self._parse_placeholders(subdirectory_name)

        scope        = MetadataScopeV2(metadata_scope)
        pnginfo_dict = None
        if scope in (MetadataScopeV2.FULL, MetadataScopeV2.PARAMETERS_ONLY) \
                or self._needs_pnginfo_for_filename(segments, extra_metadata) \
                or self._needs_pnginfo_for_filename(sub_segments, extra_metadata):
            pnginfo_dict = self._gen_pnginfo(prompt, prefer_nearest)

        filename_prefix = self._format_filename(
            filename_prefix, pnginfo_dict, segments, extra_metadata) + self.prefix_append
        subdirectory_name = self._format_filename(
            subdirectory_name, pnginfo_dict, sub_segments, extra_metadata)

        # Determine output folder. get_save_image_path handles a slash in the
        # prefix as a subfolder and returns a correct relative subfolder string.
        image_shape = images[0].shape
        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, image_shape[1], image_shape[0]
            )

        if subdirectory_name:
            full_output_folder = os.path.join(self.output_dir, subdirectory_name)
            subfolder          = subdirectory_name
            filename           = filename_prefix

        os.makedirs(full_output_folder, exist_ok=True)

        results       = []
        images_length = len(images)
        last_filename = None
        last_filepath = None
        pad           = max(1, int(numbering_padding))

        for batch_number, image in enumerate(images):
            i   = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            metadata = self._prepare_pnginfo(
                pnginfo_obj, pnginfo_dict, batch_number, images_length,
                prompt, extra_pnginfo, metadata_scope, extra_metadata
            )

            # Resolve filename
            base_name = f"{filename}_{batch_number:05d}" if include_batch_num else filename

            if filename_numbering == NumberingMode.ALWAYS.value:
                count = self._next_available_number(
                    full_output_folder, base_name, base_format,
                    start=numbering_start, padding=pad,
                )
                file = f"{base_name}_{count:0{pad}d}.{base_format}"
                path = os.path.join(full_output_folder, file)
            else:
                file = f"{base_name}.{base_format}"
                path = os.path.join(full_output_folder, file)
                if os.path.exists(path):
                    count = self._next_available_number(
                        full_output_folder, base_name, base_format,
                        start=max(1, int(numbering_start)), padding=pad,
                    )
                    file = f"{base_name}_{count:0{pad}d}.{base_format}"
                    path = os.path.join(full_output_folder, file)

            last_filename = file
            last_filepath = os.path.abspath(path)
            q             = max(1, min(100, int(quality)))

            # Save image
            if base_format == "webp":
                img.save(path, "WEBP", lossless=(q == 100), quality=q)
            elif base_format == "png":
                img.save(path, pnginfo=metadata, compress_level=self.compress_level)
            else:  # jpg
                img.save(path, optimize=True, quality=q)

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

            results.append({
                "filename":  file,
                "subfolder": full_output_folder,
                "type":      self.type,
            })

        # Optional sidecar workflow JSON
        if save_workflow_json and last_filename and extra_pnginfo:
            json_file = os.path.join(
                full_output_folder,
                last_filename[: -(len(base_format) + 1)] + ".json"
            )
            try:
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(extra_pnginfo.get("workflow", {}), f)
            except Exception as e:
                print_warning(f"Could not write workflow JSON: {e}")

        return {
            "ui":     {"images": results},
            "result": (last_filename or "", last_filepath or ""),
        }
