"""10SOR Regeneration Gate custom-node package for ComfyUI."""

try:
    from .regeneration_gate import TenSorRegenerationGate
except ImportError:  # Supports direct loading by test runners and older node loaders.
    from regeneration_gate import TenSorRegenerationGate

NODE_CLASS_MAPPINGS = {
    "10SORRegenerationGate": TenSorRegenerationGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "10SORRegenerationGate": "10SOR Regeneration Gate",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
