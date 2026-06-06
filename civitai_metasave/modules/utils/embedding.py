# =============================================================================
# Author      : Manny Gonzalez (YFG)
# Title       : YFG CivitAI MetaSave - Embedding Path Resolver
# Nickname    : YFG_CivitAI_MetaSave
# Description : Resolves the on-disk file path for a named embedding model,
#               trying several common extensions (.safetensors, .pt, .bin).
# =============================================================================

import os
import folder_paths
from ..utils.log import print_warning

embedding_directory = folder_paths.get_folder_paths("embeddings")


def get_embedding_file_path(name):
    """
    Resolve the file path for the given embedding name.

    Args:
        name (str): The name of the embedding (without extension).

    Returns:
        str | None: The resolved file path, or None if not found.
    """
    try:
        extensions = ["", ".safetensors", ".pt", ".bin"]

        for embed_dir in embedding_directory:
            if not os.path.isdir(embed_dir):
                continue

            for ext in extensions:
                path = os.path.join(embed_dir, name + ext)
                if os.path.isfile(path):
                    return path

        path = folder_paths.get_full_path("embeddings", name)
        if os.path.isfile(path):
            return path

    except Exception as e:
        print_warning(f"embedding not found '{name}': {e}")

    return None
