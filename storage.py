"""Lossless, persistent image storage for the regeneration gate."""

from __future__ import annotations

import hashlib
import inspect
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import torch


FORMAT_VERSION = 1
ENV_STORAGE_DIR = "TEN_SOR_REGEN_GATE_STORAGE_DIR"
_MAX_IDENTIFIER_BYTES = 512


class ImageStoreError(RuntimeError):
    """Base exception for persistent image-store failures."""


class ImageNotInitializedError(ImageStoreError):
    """Raised when a preserved slot has never been generated."""


class CorruptImageStateError(ImageStoreError):
    """Raised when a stored tensor cannot be trusted or decoded."""


class InvalidGateInputError(ImageStoreError):
    """Raised for invalid session, slot, or image values."""


def _validate_identifier(label: str, value: Any) -> str:
    if isinstance(value, bool):
        raise InvalidGateInputError(f"{label} must be a string or integer, not a Boolean.")
    if not isinstance(value, (str, int)):
        raise InvalidGateInputError(f"{label} must be a string or integer.")
    normalized = str(value)
    if not normalized.strip():
        raise InvalidGateInputError(f"{label} cannot be empty.")
    if "\x00" in normalized:
        raise InvalidGateInputError(f"{label} cannot contain a null byte.")
    if len(normalized.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        raise InvalidGateInputError(
            f"{label} is too long; use at most {_MAX_IDENTIFIER_BYTES} UTF-8 bytes."
        )
    return normalized


def default_storage_root() -> Path:
    override = os.environ.get(ENV_STORAGE_DIR)
    if override:
        return Path(override).expanduser().resolve()

    try:
        import folder_paths  # type: ignore
    except ImportError as exc:  # pragma: no cover - only reachable outside ComfyUI
        raise ImageStoreError(
            "ComfyUI's folder_paths module is unavailable. Run this node inside ComfyUI "
            f"or set {ENV_STORAGE_DIR} to an explicit storage directory."
        ) from exc

    return Path(folder_paths.get_user_directory()) / "10sor_regeneration_gate"


class ImageStore:
    """Stores one exact CPU tensor per session/slot in an atomic file."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root) if root is not None else default_storage_root()
        self._lock = threading.RLock()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def path_for(self, session_id: Any, slot_id: Any) -> Path:
        session = _validate_identifier("session_id", session_id)
        slot = _validate_identifier("slot_id", slot_id)
        return self.root / self._digest(session) / f"{self._digest(slot)}.pt"

    def fingerprint(self, session_id: Any, slot_id: Any) -> tuple[Any, ...]:
        """Return a cheap external-state fingerprint for ComfyUI's cache key."""

        path = self.path_for(session_id, slot_id)
        try:
            stat = path.stat()
        except FileNotFoundError:
            return ("missing",)
        except OSError as exc:
            return ("unreadable", type(exc).__name__, str(exc))
        return ("present", stat.st_size, stat.st_mtime_ns)

    @staticmethod
    def _validate_image(image: Any) -> torch.Tensor:
        if not torch.is_tensor(image):
            raise InvalidGateInputError("fresh_image must be a PyTorch IMAGE tensor.")
        if image.ndim != 4:
            raise InvalidGateInputError(
                "fresh_image must use ComfyUI's [batch, height, width, channels] layout."
            )
        if image.shape[0] < 1 or image.shape[1] < 1 or image.shape[2] < 1:
            raise InvalidGateInputError("fresh_image dimensions must all be non-zero.")
        if image.shape[3] not in (1, 3, 4):
            raise InvalidGateInputError("fresh_image must have 1, 3, or 4 channels.")
        return image

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        if os.name == "nt":
            return
        try:
            descriptor = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def save(self, session_id: Any, slot_id: Any, image: Any) -> Path:
        session = _validate_identifier("session_id", session_id)
        slot = _validate_identifier("slot_id", slot_id)
        tensor = self._validate_image(image)
        path = self.path_for(session, slot)
        payload = {
            "format_version": FORMAT_VERSION,
            "session_id": session,
            "slot_id": slot,
            "image": tensor.detach().to(device="cpu").contiguous(),
        }

        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent, delete=False
                ) as handle:
                    temporary_path = Path(handle.name)
                    torch.save(payload, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, path)
                self._fsync_directory(path.parent)
            except Exception as exc:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                raise ImageStoreError(
                    f"Could not persist the generated image for session {session!r}, slot {slot!r}: {exc}"
                ) from exc
        return path

    @staticmethod
    def _torch_load(path: Path) -> Any:
        kwargs: dict[str, Any] = {"map_location": "cpu"}
        if "weights_only" in inspect.signature(torch.load).parameters:
            kwargs["weights_only"] = True
        return torch.load(path, **kwargs)

    def load(self, session_id: Any, slot_id: Any) -> torch.Tensor:
        session = _validate_identifier("session_id", session_id)
        slot = _validate_identifier("slot_id", slot_id)
        path = self.path_for(session, slot)
        if not path.is_file():
            raise ImageNotInitializedError(
                f"10SOR Regeneration Gate session {session!r}, slot {slot!r} has no stored image. "
                "Set regenerate to TRUE and run this slot once before preserving it."
            )

        with self._lock:
            try:
                payload = self._torch_load(path)
            except Exception as exc:
                raise CorruptImageStateError(
                    f"Stored image state is unreadable for session {session!r}, slot {slot!r} "
                    f"at {path}: {exc}"
                ) from exc

        try:
            if not isinstance(payload, dict):
                raise TypeError("root value is not a mapping")
            if payload.get("format_version") != FORMAT_VERSION:
                raise ValueError(f"unsupported format version {payload.get('format_version')!r}")
            if payload.get("session_id") != session or payload.get("slot_id") != slot:
                raise ValueError("stored identifiers do not match the requested session and slot")
            image = self._validate_image(payload.get("image"))
        except Exception as exc:
            if isinstance(exc, CorruptImageStateError):
                raise
            raise CorruptImageStateError(
                f"Stored image state is invalid for session {session!r}, slot {slot!r} at {path}: {exc}"
            ) from exc
        return image


_STORE: ImageStore | None = None
_STORE_LOCK = threading.Lock()


def get_default_store() -> ImageStore:
    global _STORE
    with _STORE_LOCK:
        desired_root = default_storage_root()
        if _STORE is None or _STORE.root != desired_root:
            _STORE = ImageStore(desired_root)
        return _STORE
