# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Metadata Capture Engine
# Nickname    : YFG_CivitAI_MetaSave
# Description : Core engine that walks the live ComfyUI prompt graph,
#               extracts per-node field values via CAPTURE_FIELD_LIST,
#               assembles an A1111-compatible pnginfo dict (positive/negative
#               prompts, sampler, steps, CFG, seed, model, VAE, LoRA hashes,
#               embeddings, upscale info), and serializes it to the
#               "parameters" string format that CivitAI recognizes.
# =============================================================================

import json
import os
import re
from collections import defaultdict

from . import hook
from .defs.captures import CAPTURE_FIELD_LIST
from .defs.meta import MetaField
from .defs.formatters import calc_lora_hash, calc_model_hash, extract_embedding_names, extract_embedding_hashes
from .utils.log import print_warning
from .trace import Trace

from nodes import NODE_CLASS_MAPPINGS
from execution import get_input_data
from comfy_execution.graph import DynamicPrompt


# ---------------------------------------------------------------------------
# OutputCacheCompat
# ---------------------------------------------------------------------------

class OutputCacheCompat:
    """
    Compatibility wrapper for ComfyUI output caches across versions.

    ComfyUI 0.17+ made cache.get() async and added get_local() as the
    synchronous accessor.  We try sync paths first, falling back gracefully
    so the metadata node works across old and new ComfyUI releases.
    """

    def __init__(self, cache):
        self._cache = cache

    @staticmethod
    def _is_coroutine_like(value):
        return hasattr(value, "__await__")

    def _sync_lookup(self, input_unique_id, unique_id=None):
        cache = self._cache

        # ComfyUI 0.17+ synchronous accessor
        get_local = getattr(cache, "get_local", None)
        if callable(get_local):
            result = get_local(input_unique_id)
            if not self._is_coroutine_like(result):
                return result

        if hasattr(cache, "get_output_cache"):
            try:
                result = cache.get_output_cache(input_unique_id, unique_id)
            except TypeError:
                result = cache.get_output_cache(input_unique_id)
            if not self._is_coroutine_like(result):
                return result

        if hasattr(cache, "get_cache"):
            try:
                result = cache.get_cache(input_unique_id, unique_id)
            except TypeError:
                result = cache.get_cache(input_unique_id)
            if not self._is_coroutine_like(result):
                return result

        if isinstance(cache, dict):
            return cache.get(input_unique_id)

        outputs_attr = getattr(cache, "outputs", None)
        if isinstance(outputs_attr, dict):
            return outputs_attr.get(input_unique_id)

        get_fn = getattr(cache, "get", None)
        if callable(get_fn):
            try:
                result = get_fn(input_unique_id)
                if self._is_coroutine_like(result):
                    return None
                return result
            except Exception:
                return None

        return None

    def get_output_cache(self, input_unique_id, unique_id=None):
        return self._sync_lookup(input_unique_id, unique_id)

    def get(self, input_unique_id):
        return self._sync_lookup(input_unique_id)

    def get_cache(self, input_unique_id, unique_id=None):
        return self._sync_lookup(input_unique_id, unique_id)


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

class Capture:

    @classmethod
    def get_inputs(cls):
        inputs  = {}
        prompt  = hook.current_prompt
        extra_data = hook.current_extra_data

        if hook.prompt_executer and hook.prompt_executer.caches:
            outputs = OutputCacheCompat(hook.prompt_executer.caches.outputs)
        else:
            outputs = None

        for node_id, obj in prompt.items():
            class_type  = obj["class_type"]
            obj_class   = NODE_CLASS_MAPPINGS.get(class_type)
            if obj_class is None:
                continue
            node_inputs = obj["inputs"]

            input_data = get_input_data(
                node_inputs, obj_class, node_id, outputs,
                DynamicPrompt(prompt), extra_data
            )

            for node_class, metas in CAPTURE_FIELD_LIST.items():
                if class_type != node_class:
                    continue

                for meta, field_data in metas.items():
                    if field_data.get("validate") and not field_data["validate"](
                        node_id, obj, prompt, extra_data, outputs, input_data
                    ):
                        continue

                    if meta not in inputs:
                        inputs[meta] = []

                    value = field_data.get("value")
                    if value is not None:
                        inputs[meta].append((node_id, value))
                        continue

                    selector = field_data.get("selector")
                    if selector:
                        v = selector(node_id, obj, prompt, extra_data, outputs, input_data)
                        cls._append_value(inputs, meta, node_id, v)
                        continue

                    field_name = field_data["field_name"]
                    value = input_data[0].get(field_name)
                    if value is not None:
                        fmt = field_data.get("format")
                        v   = cls._apply_formatting(value, input_data, fmt)
                        cls._append_value(inputs, meta, node_id, v)

        return inputs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_formatting(value, input_data, format_func):
        if isinstance(value, list) and len(value) > 0:
            value = value[0]
        if format_func:
            value = format_func(value, input_data)
        return value

    @staticmethod
    def _append_value(inputs, meta, node_id, value):
        if isinstance(value, list):
            for x in value:
                inputs[meta].append((node_id, x))
        elif value is not None:
            inputs[meta].append((node_id, value))

    # ------------------------------------------------------------------
    # LoRA extraction
    # ------------------------------------------------------------------

    @classmethod
    def get_lora_strings_and_hashes(cls, inputs_before_sampler_node):

        def clean_name(n):
            return (os.path.splitext(os.path.basename(n))[0]
                    .replace("\\", "_").replace("/", "_")
                    .replace(" ", "_").replace(":", "_"))

        lora_assertion_re = re.compile(r"<(lora|lyco):([a-zA-Z0-9_\./\\-]+):([0-9.]+)>")

        prompt_texts = [
            val[1]
            for key in [MetaField.POSITIVE_PROMPT, MetaField.NEGATIVE_PROMPT]
            for val in inputs_before_sampler_node.get(key, [])
            if isinstance(val[1], str)
        ]
        prompt_joined = " ".join(prompt_texts).replace("\n", " ").replace("\r", " ").lower()

        lora_names   = inputs_before_sampler_node.get(MetaField.LORA_MODEL_NAME,      [])
        lora_weights = inputs_before_sampler_node.get(MetaField.LORA_STRENGTH_MODEL,  [])
        lora_hashes  = inputs_before_sampler_node.get(MetaField.LORA_MODEL_HASH,      [])

        # Parse LoRAs embedded directly in the prompt text
        lora_names_from_prompt   = []
        lora_weights_from_prompt = []
        lora_hashes_from_prompt  = []

        if "<lora:" in prompt_joined:
            for text in prompt_texts:
                for _, name, weight in re.findall(
                    lora_assertion_re, text.replace("\n", " ").replace("\r", " ")
                ):
                    lora_names_from_prompt.append(("prompt_parse", name))
                    lora_weights_from_prompt.append(("prompt_parse", float(weight)))
                    h = calc_lora_hash(name)
                    if h:
                        lora_hashes_from_prompt.append(("prompt_parse", h))

        all_names   = lora_names   + lora_names_from_prompt
        all_weights = lora_weights + lora_weights_from_prompt
        all_hashes  = lora_hashes  + lora_hashes_from_prompt

        inputs_before_sampler_node[MetaField.LORA_MODEL_NAME]     = all_names
        inputs_before_sampler_node[MetaField.LORA_STRENGTH_MODEL] = all_weights
        inputs_before_sampler_node[MetaField.LORA_MODEL_HASH]     = all_hashes

        grouped = defaultdict(list)
        for name, weight, hsh in zip(all_names, all_weights, all_hashes):
            if not (name and weight and hsh):
                continue
            grouped[(hsh[1], weight[1])].append(clean_name(name[1]))

        hashes_in_prompt = {h[1].lower() for h in lora_hashes_from_prompt}

        lora_strings, lora_hashes_list = [], []
        for (hsh, weight), names in grouped.items():
            canonical = min(names, key=len)
            present   = hsh.lower() in hashes_in_prompt
            if not present:
                lora_strings.append(f"<lora:{canonical}:{weight}>")
            lora_hashes_list.append(f"{canonical}: {hsh}")

        # Rewrite prompt with cleaned LoRA names
        updated_prompts = []
        if "<lora:" in prompt_joined:
            for text in prompt_texts:
                def replace(m):
                    tag, raw_name, weight = m.group(1), m.group(2), m.group(3)
                    return f"<{tag}:{clean_name(raw_name)}:{weight}>"
                updated_prompts.append(lora_assertion_re.sub(replace, text))
        else:
            updated_prompts = prompt_texts

        lora_hashes_string = ", ".join(lora_hashes_list)
        return lora_strings, lora_hashes_string, updated_prompts

    # ------------------------------------------------------------------
    # pnginfo dict assembly
    # ------------------------------------------------------------------

    @classmethod
    def gen_pnginfo_dict(cls, inputs_before_sampler_node, inputs_before_this_node, prompt,
                         save_civitai_sampler=True):
        pnginfo = {}

        if not inputs_before_sampler_node:
            inputs_before_sampler_node = defaultdict(list)
            cls._collect_all_metadata(prompt, inputs_before_sampler_node)

        def is_simple(value):
            return isinstance(value, (str, int, float, bool)) or value is None

        def extract(meta_key, label, source=inputs_before_sampler_node):
            for link in source.get(meta_key, []):
                if len(link) <= 1:
                    continue
                candidate = link[1]
                if candidate is None:
                    continue
                if isinstance(candidate, str):
                    if not candidate.strip():
                        continue
                elif not is_simple(candidate):
                    continue
                value = str(candidate)
                pnginfo[label] = value
                return value
            return None

        # Prompts
        positive = extract(MetaField.POSITIVE_PROMPT, "Positive prompt") or ""
        if not positive.strip():
            print_warning("Positive prompt is empty!")

        negative = extract(MetaField.NEGATIVE_PROMPT, "Negative prompt") or ""
        lora_strings, lora_hashes, updated_prompts = cls.get_lora_strings_and_hashes(
            inputs_before_sampler_node
        )

        if updated_prompts:
            positive = updated_prompts[0]

        if lora_strings:
            positive += " " + " ".join(lora_strings)

        pnginfo["Positive prompt"] = positive.strip()
        pnginfo["Negative prompt"] = negative.strip()

        # Sampling params – abort early if Steps missing (CivitAI requires it)
        if not extract(MetaField.STEPS, "Steps"):
            print_warning("Steps are empty – full metadata will not be written!")
            return {}

        samplers   = inputs_before_sampler_node.get(MetaField.SAMPLER_NAME)
        schedulers = inputs_before_sampler_node.get(MetaField.SCHEDULER)

        if save_civitai_sampler:
            pnginfo["Sampler"] = cls.get_sampler_for_civitai(samplers, schedulers)
        elif samplers:
            sampler_name = samplers[0][1]
            if schedulers and schedulers[0][1] != "normal":
                sampler_name += f"_{schedulers[0][1]}"
            pnginfo["Sampler"] = sampler_name

        extract(MetaField.CFG,  "CFG scale")
        extract(MetaField.SEED, "Seed")

        clip_skip = extract(MetaField.CLIP_SKIP, "Clip skip")
        if clip_skip is None:
            pnginfo["Clip skip"] = "1"

        # Image size
        def extract_dim(data):
            return data[0][1] if data and len(data[0]) > 1 and isinstance(data[0][1], int) else None

        width  = extract_dim(inputs_before_sampler_node.get(MetaField.IMAGE_WIDTH,  [[]]))
        height = extract_dim(inputs_before_sampler_node.get(MetaField.IMAGE_HEIGHT, [[]]))
        if width and height:
            pnginfo["Size"] = f"{width}x{height}"

        # Model + VAE
        extract(MetaField.MODEL_NAME, "Model")
        extract(MetaField.MODEL_HASH, "Model hash")
        extract(MetaField.VAE_NAME,   "VAE",      inputs_before_this_node)
        extract(MetaField.VAE_HASH,   "VAE hash", inputs_before_this_node)

        # Denoising
        denoise = inputs_before_sampler_node.get(MetaField.DENOISE)
        dval    = denoise[0][1] if denoise else None
        if dval and 0 < float(dval) < 1:
            pnginfo["Denoising strength"] = float(dval)

        if inputs_before_this_node.get(MetaField.UPSCALE_BY) or \
           inputs_before_this_node.get(MetaField.UPSCALE_MODEL_NAME):
            pnginfo["Denoising strength"] = float(dval or 1.0)

        extract(MetaField.UPSCALE_BY,         "Hires upscale",   inputs_before_this_node)
        extract(MetaField.UPSCALE_MODEL_NAME,  "Hires upscaler",  inputs_before_this_node)

        if lora_hashes:
            pnginfo["Lora hashes"] = f'"{lora_hashes}"'

        pnginfo.update(cls.gen_loras(inputs_before_sampler_node))
        pnginfo.update(cls.gen_embeddings(inputs_before_sampler_node))

        hashes = cls.get_hashes_for_civitai(inputs_before_sampler_node, inputs_before_this_node)
        if hashes:
            pnginfo["Hashes"] = json.dumps(hashes)

        return pnginfo

    # ------------------------------------------------------------------
    # Fallback metadata collection (no sampler node found)
    # ------------------------------------------------------------------

    @classmethod
    def _collect_all_metadata(cls, prompt, result_dict):
        def _append(meta, node_id, value):
            if value is not None:
                result_dict[meta].append((node_id, value, 0))

        resolved = {
            "prompt":  Trace.find_node_with_fields(prompt, {"positive", "negative"}),
            "denoise": Trace.find_node_with_fields(prompt, {"denoise"}),
            "sampler": Trace.find_node_with_fields(prompt, {"seed", "steps", "cfg", "sampler_name", "scheduler"}),
            "size":    Trace.find_node_with_fields(prompt, {"width", "height"}),
            "model":   Trace.find_node_with_fields(prompt, {"ckpt_name"}),
        }

        for node_id, node in Trace.find_all_nodes_with_fields(prompt, {"lora_name", "strength_model"}):
            if node is not None:
                inputs = node.get("inputs", {})
                name   = inputs.get("lora_name")
                strength = inputs.get("strength_model")
                _append(MetaField.LORA_MODEL_NAME,     node_id, name)
                _append(MetaField.LORA_MODEL_HASH,     node_id, calc_lora_hash(name) if name else None)
                _append(MetaField.LORA_STRENGTH_MODEL, node_id, strength)

        model_node = resolved.get("model")
        if model_node and model_node[1] is not None:
            node_id, node = model_node
            name = node.get("inputs", {}).get("ckpt_name")
            _append(MetaField.MODEL_NAME, node_id, name)
            _append(MetaField.MODEL_HASH, node_id, calc_model_hash(name) if name else None)

        denoise_node = resolved.get("denoise")
        if denoise_node and denoise_node[1] is not None:
            node_id, node = denoise_node
            _append(MetaField.DENOISE, node_id, node.get("inputs", {}).get("denoise"))

        sampler_node = resolved.get("sampler")
        if sampler_node and sampler_node[1] is not None:
            node_id, node = sampler_node
            inputs = node.get("inputs", {})
            for key, meta in {
                "sampler_name": MetaField.SAMPLER_NAME,
                "scheduler":    MetaField.SCHEDULER,
                "seed":         MetaField.SEED,
                "steps":        MetaField.STEPS,
                "cfg":          MetaField.CFG,
            }.items():
                _append(meta, node_id, inputs.get(key))

        size_node = resolved.get("size")
        if size_node and size_node[1] is not None:
            node_id, node = size_node
            inputs = node.get("inputs", {})
            _append(MetaField.IMAGE_WIDTH,  node_id, inputs.get("width"))
            _append(MetaField.IMAGE_HEIGHT, node_id, inputs.get("height"))

        for node_id, node in Trace.find_all_nodes_with_fields(prompt, {"positive", "negative"}):
            if node is not None:
                inputs = node.get("inputs", {})
                def resolve_text(ref):
                    if isinstance(ref, list):
                        ref = ref[0]
                    if not isinstance(ref, str):
                        return None
                    n = prompt.get(ref)
                    return n.get("inputs", {}).get("text") if n else None

                pos_ref = inputs.get("positive", [None])[0]
                neg_ref = inputs.get("negative", [None])[0]
                pos_text = resolve_text(pos_ref)
                neg_text = resolve_text(neg_ref)

                _append(MetaField.POSITIVE_PROMPT, pos_ref, pos_text)
                _append(MetaField.NEGATIVE_PROMPT, neg_ref, neg_text)

                for text, is_pos in [(pos_text, True), (neg_text, False)]:
                    if text:
                        for name, h in zip(
                            extract_embedding_names(text),
                            extract_embedding_hashes(text)
                        ):
                            _append(MetaField.EMBEDDING_NAME, node_id, name)
                            _append(MetaField.EMBEDDING_HASH, node_id, h)

    # ------------------------------------------------------------------
    # LoRA / Embedding helper formatters
    # ------------------------------------------------------------------

    @classmethod
    def extract_model_info(cls, inputs, meta_field_name, prefix):
        result = {}
        names  = inputs.get(meta_field_name, [])
        hashes = inputs.get(f"{meta_field_name}_HASH", [])
        for i, (name, hsh) in enumerate(zip(names, hashes)):
            fp = f"{prefix}_{i}"
            result[f"{fp} name"] = os.path.splitext(os.path.basename(name[1]))[0]
            result[f"{fp} hash"] = hsh[1]
        return result

    @classmethod
    def gen_loras(cls, inputs):
        return cls.extract_model_info(inputs, MetaField.LORA_MODEL_NAME, "Lora")

    @classmethod
    def gen_embeddings(cls, inputs):
        return cls.extract_model_info(inputs, MetaField.EMBEDDING_NAME, "Embedding")

    # ------------------------------------------------------------------
    # CivitAI hash bundle
    # ------------------------------------------------------------------

    @classmethod
    def get_hashes_for_civitai(cls, inputs_before_sampler_node, inputs_before_this_node):
        def single(inputs, key):
            items = inputs.get(key, [])
            return items[0][1] if items and len(items[0]) > 1 else None

        def named(names, hashes, prefix):
            result = {}
            for n, h in zip(names, hashes):
                base = os.path.splitext(os.path.basename(n[1]))[0]
                result[f"{prefix}:{base}"] = h[1]
            return result

        resource_hashes = {}

        model = single(inputs_before_sampler_node, MetaField.MODEL_HASH)
        if model:
            resource_hashes["model"] = model

        vae = single(inputs_before_this_node, MetaField.VAE_HASH)
        if vae:
            resource_hashes["vae"] = vae

        upscaler = single(inputs_before_this_node, MetaField.UPSCALE_MODEL_HASH)
        if upscaler:
            resource_hashes["upscaler"] = upscaler

        resource_hashes.update(named(
            inputs_before_sampler_node.get(MetaField.LORA_MODEL_NAME, []),
            inputs_before_sampler_node.get(MetaField.LORA_MODEL_HASH, []),
            "lora"
        ))
        resource_hashes.update(named(
            inputs_before_sampler_node.get(MetaField.EMBEDDING_NAME, []),
            inputs_before_sampler_node.get(MetaField.EMBEDDING_HASH, []),
            "embed"
        ))

        return resource_hashes

    # ------------------------------------------------------------------
    # Sampler name → CivitAI pretty name
    # ------------------------------------------------------------------

    @classmethod
    def get_sampler_for_civitai(cls, sampler_names, schedulers):
        SAMPLER_MAP = {
            "euler":             "Euler",
            "euler_ancestral":   "Euler a",
            "heun":              "Heun",
            "dpm_2":             "DPM2",
            "dpm_2_ancestral":   "DPM2 a",
            "lms":               "LMS",
            "dpm_fast":          "DPM fast",
            "dpm_adaptive":      "DPM adaptive",
            "dpmpp_2s_ancestral":"DPM++ 2S a",
            "dpmpp_sde":         "DPM++ SDE",
            "dpmpp_sde_gpu":     "DPM++ SDE",
            "dpmpp_2m":          "DPM++ 2M",
            "dpmpp_2m_sde":      "DPM++ 2M SDE",
            "dpmpp_2m_sde_gpu":  "DPM++ 2M SDE",
            "ddim":              "DDIM",
            "plms":              "PLMS",
            "uni_pc":            "UniPC",
            "uni_pc_bh2":        "UniPC",
            "lcm":               "LCM",
        }

        sampler   = sampler_names[0][1] if sampler_names else None
        scheduler = schedulers[0][1]    if schedulers    else None

        if not sampler:
            return None

        def with_scheduler(name):
            if scheduler == "karras":
                return f"{name} Karras"
            elif scheduler == "exponential":
                return f"{name} Exponential"
            elif not scheduler or scheduler == "normal":
                return name
            else:
                return f"{name}_{scheduler}"

        if sampler in SAMPLER_MAP:
            return with_scheduler(SAMPLER_MAP[sampler])
        return with_scheduler(sampler)

    # ------------------------------------------------------------------
    # A1111-format parameters string
    # ------------------------------------------------------------------

    @classmethod
    def gen_parameters_str(cls, pnginfo_dict):
        if not pnginfo_dict or not isinstance(pnginfo_dict, dict):
            return ""

        def clean(value):
            return str(value).strip().replace("\n", " ") if value is not None else ""

        def strip_embedding_prefix(text):
            return text.replace("embedding:", "")

        cleaned = {k: clean(v) for k, v in pnginfo_dict.items()}
        pos = strip_embedding_prefix(cleaned.get("Positive prompt", ""))
        neg = strip_embedding_prefix(cleaned.get("Negative prompt", ""))

        result = [pos]
        if neg:
            result.append(f"Negative prompt: {neg}")

        params = ", ".join(
            f"{k}: {v}"
            for k, v in cleaned.items()
            if k not in {"Positive prompt", "Negative prompt"} and v not in {None, ""}
        )
        result.append(params)
        return "\n".join(result)
