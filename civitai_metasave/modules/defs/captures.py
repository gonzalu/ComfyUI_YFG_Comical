# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Capture Field List
# Nickname    : YFG_CivitAI_MetaSave
# Description : Master mapping of ComfyUI node class names to the metadata
#               fields they contribute, with optional format functions and
#               validators. Covers classic SD, Flux, SD3, Ideogram, LoRA,
#               upscale, and embedding workflows.
#
# Changelog
# ---------
# v1.7.3  Add TextEncodeQwenImageEditPlus support (Krea2 / Qwen VLM encoder).
#         Krea2 workflows use this node instead of CLIPTextEncode, with the
#         prompt in a field named "prompt" rather than "text". Without this
#         entry the extension captures trigger words only and misses the
#         actual positive/negative prompt entirely.
#
# v1.7.2  Add Power Lora Loader (rgthree) support via selector functions.
#         rgthree's node stores LoRAs as lora_1..N dicts with {on, lora,
#         strength} rather than standard lora_name/strength_model widgets,
#         so it was silently skipped by the field-name capture path.
#         Active entries (on=True) are now enumerated, hashed, and reported
#         correctly in CivitAI metadata. Resolves missing LoRA hashes for
#         any workflow using Power Lora Loader (rgthree).
# =============================================================================

from .meta import MetaField
from .validators import (
    is_positive_prompt,
    is_distinct_negative_prompt,
    is_latent_executed,
    is_primary_unet_model,
)
from .formatters import (
    calc_model_hash,
    calc_upscale_hash,
    calc_vae_hash,
    calc_lora_hash,
    calc_unet_hash,
    convert_skip_clip,
    get_scaled_width,
    get_scaled_height,
    extract_embedding_names,
    extract_embedding_hashes,
)


# =============================================================================
# Selector helpers for Power Lora Loader (rgthree)
#
# rgthree's Power Lora Loader stores LoRAs as lora_1, lora_2, ... dict inputs
# with the structure: {"on": bool, "lora": "path/name.safetensors", "strength": float}
# rather than the standard lora_name / strength_model widget fields used by
# ComfyUI's built-in LoraLoader.  We use selector functions so get_inputs()
# can extract multiple active LoRA entries from a single node pass.
# =============================================================================

def _power_lora_active_entries(obj):
    """Return a list of active lora entry dicts from a Power Lora Loader node."""
    entries = []
    for key, val in obj.get("inputs", {}).items():
        if key.startswith("lora_") and isinstance(val, dict) and val.get("on", False):
            lora_path = val.get("lora")
            if lora_path:
                entries.append(val)
    return entries

def _power_lora_names(node_id, obj, prompt, extra_data, outputs, input_data):
    return [e["lora"] for e in _power_lora_active_entries(obj)]

def _power_lora_hashes(node_id, obj, prompt, extra_data, outputs, input_data):
    return [calc_lora_hash(e["lora"]) for e in _power_lora_active_entries(obj)]

def _power_lora_strengths(node_id, obj, prompt, extra_data, outputs, input_data):
    return [e.get("strength", 1.0) for e in _power_lora_active_entries(obj)]


CAPTURE_FIELD_LIST = {
    # ---------------------------------------------------------
    # Core: base checkpoint / model loading
    # ---------------------------------------------------------
    "CheckpointLoaderSimple": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
    },

    "CLIPSetLastLayer": {
        MetaField.CLIP_SKIP: {
            "field_name": "stop_at_clip_layer",
            "format": convert_skip_clip,
        },
    },

    "VAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },

    "EmptyLatentImage": {
        MetaField.IMAGE_WIDTH:  {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },

    # ---------------------------------------------------------
    # Prompts / CLIP — standard encoder
    # ---------------------------------------------------------
    "CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {
            "field_name": "text",
            "validate": is_positive_prompt,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "text",
            "validate": is_distinct_negative_prompt,
        },
        MetaField.EMBEDDING_NAME: {
            "field_name": "text",
            "format": extract_embedding_names,
        },
        MetaField.EMBEDDING_HASH: {
            "field_name": "text",
            "format": extract_embedding_hashes,
        },
    },

    # ---------------------------------------------------------
    # Prompts / CLIP — Krea2 / Qwen VLM encoder
    #
    # TextEncodeQwenImageEditPlus is Krea2's multimodal text+image
    # encoder. It uses "prompt" as the text field name instead of
    # "text", and is the ONLY active conditioner in Krea2 workflows
    # (CLIPTextEncode nodes are muted). Without this entry the
    # extension captures trigger words but misses the actual prompt.
    # ---------------------------------------------------------
    "TextEncodeQwenImageEditPlus": {
        MetaField.POSITIVE_PROMPT: {
            "field_name": "prompt",
            "validate": is_positive_prompt,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "prompt",
            "validate": is_distinct_negative_prompt,
        },
        MetaField.EMBEDDING_NAME: {
            "field_name": "prompt",
            "format": extract_embedding_names,
        },
        MetaField.EMBEDDING_HASH: {
            "field_name": "prompt",
            "format": extract_embedding_hashes,
        },
    },

    # ---------------------------------------------------------
    # Classic KSampler nodes
    # ---------------------------------------------------------
    "KSampler": {
        MetaField.SEED:         {"field_name": "seed"},
        MetaField.STEPS:        {"field_name": "steps"},
        MetaField.CFG:          {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER:    {"field_name": "scheduler"},
        MetaField.DENOISE:      {"field_name": "denoise"},
    },

    "KSamplerAdvanced": {
        MetaField.SEED:         {"field_name": "noise_seed"},
        MetaField.STEPS:        {"field_name": "steps"},
        MetaField.CFG:          {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER:    {"field_name": "scheduler"},
    },

    # ---------------------------------------------------------
    # Latent size / upscaling
    # ---------------------------------------------------------
    "LatentUpscale": {
        MetaField.IMAGE_WIDTH:  {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },

    "LatentUpscaleBy": {
        MetaField.IMAGE_WIDTH: {
            "field_name": "scale_by",
            "format": get_scaled_width,
            "validate": is_latent_executed,
        },
        MetaField.IMAGE_HEIGHT: {
            "field_name": "scale_by",
            "format": get_scaled_height,
            "validate": is_latent_executed,
        },
    },

    # ---------------------------------------------------------
    # LoRA — standard ComfyUI built-in nodes
    # ---------------------------------------------------------
    "LoraLoader": {
        MetaField.LORA_MODEL_NAME:     {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH:     {"field_name": "lora_name", "format": calc_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP:  {"field_name": "strength_clip"},
    },

    "LoraLoaderModelOnly": {
        MetaField.LORA_MODEL_NAME:     {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH:     {"field_name": "lora_name", "format": calc_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP:  {"value": 0},
    },

    # ---------------------------------------------------------
    # LoRA — rgthree Power Lora Loader
    #
    # This node stores LoRAs as lora_1..lora_N dicts rather than
    # individual lora_name widgets, so selector functions are
    # used to iterate all active (on=True) entries per node pass.
    # Multiple Power Lora Loader nodes in a workflow are each
    # processed in turn, accumulating all active LoRAs.
    # ---------------------------------------------------------
    "Power Lora Loader (rgthree)": {
        MetaField.LORA_MODEL_NAME:     {"selector": _power_lora_names},
        MetaField.LORA_MODEL_HASH:     {"selector": _power_lora_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": _power_lora_strengths},
    },

    # ---------------------------------------------------------
    # Upscale models
    # ---------------------------------------------------------
    "UpscaleModelLoader": {
        MetaField.UPSCALE_MODEL_NAME: {"field_name": "model_name"},
        MetaField.UPSCALE_MODEL_HASH: {"field_name": "model_name", "format": calc_upscale_hash},
    },

    "ImageScaleBy": {
        MetaField.UPSCALE_BY: {"field_name": "scale_by"},
    },

    # ---------------------------------------------------------
    # Flux / SD3 / Ideogram – model + schedulers + helpers
    # ---------------------------------------------------------
    "UNETLoader": {
        MetaField.MODEL_NAME: {
            "field_name": "unet_name",
            "validate": is_primary_unet_model,
        },
        MetaField.MODEL_HASH: {
            "field_name": "unet_name",
            "format": calc_unet_hash,
            "validate": is_primary_unet_model,
        },
    },

    "RandomNoise": {
        MetaField.SEED: {"field_name": "noise_seed"},
    },

    "BasicScheduler": {
        MetaField.STEPS:     {"field_name": "steps"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
        MetaField.DENOISE:   {"field_name": "denoise"},
    },

    "BetaSamplingScheduler": {
        MetaField.STEPS: {"field_name": "steps"},
    },

    "Flux2Scheduler": {
        MetaField.STEPS: {"field_name": "steps"},
    },

    "Ideogram4Scheduler": {
        MetaField.STEPS: {"field_name": "steps"},
    },

    "KSamplerSelect": {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
    },

    "CFGGuider": {
        MetaField.CFG: {"field_name": "cfg"},
    },

    "DualModelGuider": {
        MetaField.CFG: {"field_name": "cfg"},
    },

    "SamplerCustom": {
        MetaField.CFG:  {"field_name": "cfg"},
        MetaField.SEED: {"field_name": "noise_seed"},
    },

    # ---------------------------------------------------------
    # Empty latent nodes used by Flux2 / SD3 / Ideogram
    # ---------------------------------------------------------
    "EmptyFlux2LatentImage": {
        MetaField.IMAGE_WIDTH:  {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },

    "EmptySD3LatentImage": {
        MetaField.IMAGE_WIDTH:  {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },
}
