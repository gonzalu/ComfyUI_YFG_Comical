"""
@creator: YFG
@title: YFG Smart Checkpoint Loader
@nickname: 🧠 YFG Smart Checkpoint Loader
@description: This extension loads a model checkpoint file and extracts the model state dictionary or the entire model, treating all checkpoints as if they are in the root directory.
"""

import os
import torch
import folder_paths
import comfy.sd

class SmartCheckpointLoader:
    def __init__(self):
        # Create a mapping of checkpoint basenames to their full paths
        self.ckpt_name_to_path = self.remap_checkpoints_to_root()

    @classmethod
    def INPUT_TYPES(s):
        # Get the list of checkpoint files with their full paths
        ckpt_files = folder_paths.get_filename_list("checkpoints")
        # Use the basename of the checkpoints for the input options
        ckpt_names = [os.path.basename(ckpt) for ckpt in ckpt_files]
        return {"required": {"ckpt_name": (ckpt_names,)}}

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load_checkpoint"
    CATEGORY = "🐯 YFG/🔄 Loaders"

    def load_checkpoint(self, ckpt_name, output_vae=True, output_clip=True):
        # Get the full path from the mapping
        ckpt_path = self.ckpt_name_to_path.get(ckpt_name)
        if ckpt_path is None:
            raise FileNotFoundError(f"Checkpoint file not found: {ckpt_name}")
        out = comfy.sd.load_checkpoint_guess_config(
            ckpt_path, output_vae=output_vae, output_clip=output_clip, embedding_directory=folder_paths.get_folder_paths("embeddings")
        )
        return out[:3]

    def remap_checkpoints_to_root(self):
        # Get the list of all checkpoint files including subdirectories
        checkpoint_files = folder_paths.get_filename_list("checkpoints")
        remapped_files = {}

        for ckpt in checkpoint_files:
            remapped_files[os.path.basename(ckpt)] = folder_paths.get_full_path("checkpoints", ckpt)

        return remapped_files

# Initialize the node to create the path mapping
node = SmartCheckpointLoader()
