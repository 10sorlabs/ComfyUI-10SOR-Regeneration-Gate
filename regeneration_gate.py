"""ComfyUI node that lazily regenerates or restores one carousel image."""

from __future__ import annotations

from typing import Any

try:
    from .storage import ImageStore, InvalidGateInputError, get_default_store
except ImportError:  # Supports direct loading by test runners and older node loaders.
    from storage import ImageStore, InvalidGateInputError, get_default_store


class TenSorRegenerationGate:
    """Persist fresh images and skip their entire upstream branch when preserved."""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "execute"
    CATEGORY = "10sorLabs"
    DESCRIPTION = (
        "TRUE evaluates and stores fresh_image. FALSE skips the upstream branch and restores "
        "the last successful image for this session and slot."
    )
    SEARCH_ALIASES = ["regeneration gate", "image lock", "preserve image", "10sor"]

    def __init__(self, store: ImageStore | None = None):
        self._store = store

    @property
    def store(self) -> ImageStore:
        return self._store if self._store is not None else get_default_store()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "fresh_image": (
                    "IMAGE",
                    {
                        "lazy": True,
                        "tooltip": "Final image from this slot's generation/enhancement branch.",
                    },
                ),
                "regenerate": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "REGENERATE",
                        "label_off": "PRESERVE",
                        "tooltip": "TRUE generates a fresh image; FALSE restores the saved image.",
                    },
                ),
                "session_id": (
                    "STRING",
                    {
                        "default": "carousel-001",
                        "multiline": False,
                        "tooltip": "Use the same value for all four slots; change it for a new carousel.",
                    },
                ),
                "slot_id": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 4,
                        "step": 1,
                        "tooltip": "Unique slot number within this carousel session.",
                    },
                ),
            }
        }

    def check_lazy_status(
        self,
        regenerate: bool,
        session_id: str,
        slot_id: int,
        fresh_image: Any | None = None,
    ) -> list[str]:
        if not isinstance(regenerate, bool):
            raise InvalidGateInputError("regenerate must be a Boolean.")
        # Validate identifiers even while locked, before deciding whether to request the branch.
        self.store.path_for(session_id, slot_id)
        if regenerate and fresh_image is None:
            return ["fresh_image"]
        return []

    def execute(
        self,
        regenerate: bool,
        session_id: str,
        slot_id: int,
        fresh_image: Any | None = None,
    ):
        if not isinstance(regenerate, bool):
            raise InvalidGateInputError("regenerate must be a Boolean.")
        if regenerate:
            if fresh_image is None:
                raise InvalidGateInputError(
                    "fresh_image was not evaluated while regenerate is TRUE. "
                    "Check the input connection and ComfyUI lazy-execution support."
                )
            self.store.save(session_id, slot_id, fresh_image)
            return (fresh_image,)
        return (self.store.load(session_id, slot_id),)

    @classmethod
    def IS_CHANGED(
        cls,
        regenerate: bool,
        session_id: str,
        slot_id: int,
        fresh_image: Any | None = None,
    ):
        # Linked values are intentionally unavailable to IS_CHANGED. The normal ancestry
        # signature covers fresh_image. Locked mode also tracks external state so deletion or
        # replacement of the durable file invalidates ComfyUI's in-memory node cache.
        if regenerate:
            return ("regenerate",)
        return ("preserve",) + get_default_store().fingerprint(session_id, slot_id)
