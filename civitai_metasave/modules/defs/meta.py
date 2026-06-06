# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Meta Field Definitions
# Nickname    : YFG_CivitAI_MetaSave
# Description : Enum of internal metadata field keys used across the
#               capture, trace, and formatting pipeline.
# =============================================================================

from enum import IntEnum


class MetaField(IntEnum):
    MODEL_NAME           = 0
    MODEL_HASH           = 1
    VAE_NAME             = 2
    VAE_HASH             = 3
    POSITIVE_PROMPT      = 10
    NEGATIVE_PROMPT      = 11
    CLIP_SKIP            = 12
    SEED                 = 20
    STEPS                = 21
    CFG                  = 22
    SAMPLER_NAME         = 23
    SCHEDULER            = 24
    DENOISE              = 26
    IMAGE_WIDTH          = 30
    IMAGE_HEIGHT         = 31
    EMBEDDING_NAME       = 40
    EMBEDDING_HASH       = 41
    LORA_MODEL_NAME      = 50
    LORA_MODEL_HASH      = 51
    LORA_STRENGTH_MODEL  = 52
    LORA_STRENGTH_CLIP   = 53
    UPSCALE_MODEL_NAME   = 80
    UPSCALE_MODEL_HASH   = 81
    UPSCALE_BY           = 83
