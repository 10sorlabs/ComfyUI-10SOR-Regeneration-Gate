"""Native BOOLEAN outputs for the adaptive 10SOR control panel.

The frontend only *displays* the connected outputs plus one free socket.
The backend exposes a generous, fixed execution capacity because ComfyUI's
legacy RETURN_TYPES metadata is static and links must survive subgraph
flattening. Only the sockets used in the workflow are serialized.
"""

from __future__ import annotations

import json

MAX_CONTROL_SLOTS = 1024


class TenSorRegenerationControlPanel:
    CATEGORY = "10sorLabs"
    DESCRIPTION = (
        "Adaptive per-image REGENERATE/PRESERVE switches. "
        "Connect the last output to reveal another. Toggle all sets every switch."
    )
    FUNCTION = "execute"
    RETURN_TYPES = ("BOOLEAN",) * MAX_CONTROL_SLOTS
    RETURN_NAMES = tuple(f"Image {index:02d}" for index in range(1, MAX_CONTROL_SLOTS + 1))
    SEARCH_ALIASES = ["regeneration control", "toggle all", "10sor boolean panel"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "values_json": (
                    "STRING",
                    {
                        "default": "[]",
                        "multiline": False,
                        "tooltip": "Internal control-panel state. Managed by the panel's frontend switches.",
                    },
                ),
            },
        }

    @staticmethod
    def _parse(values_json: str) -> list[bool]:
        try:
            values = json.loads(values_json)
        except (TypeError, ValueError) as exc:
            raise ValueError("10SOR control panel state is not valid JSON.") from exc
        if not isinstance(values, list) or len(values) > MAX_CONTROL_SLOTS:
            raise ValueError("10SOR control panel state must be an array within slot capacity.")
        if not all(isinstance(item, bool) for item in values):
            raise ValueError("10SOR control panel values must all be booleans.")
        return values

    def execute(self, values_json: str):
        values = self._parse(values_json)
        return tuple(values[i] if i < len(values) else True for i in range(MAX_CONTROL_SLOTS))
