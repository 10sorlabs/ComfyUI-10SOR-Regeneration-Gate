"""10SOR Regeneration Gate custom-node package for ComfyUI."""

try:
    from .regeneration_gate import TenSorRegenerationGate
    from .control_panel import TenSorRegenerationControlPanel
except ImportError:  # Supports direct loading by test runners and older node loaders.
    from regeneration_gate import TenSorRegenerationGate
    from control_panel import TenSorRegenerationControlPanel

NODE_CLASS_MAPPINGS = {
    "10SORRegenerationGate": TenSorRegenerationGate,
    "10SORRegenerationControlPanel": TenSorRegenerationControlPanel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "10SORRegenerationGate": "10SOR Regeneration Gate",
    "10SORRegenerationControlPanel": "10SOR Regeneration Control Panel",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
