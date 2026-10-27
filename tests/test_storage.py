from __future__ import annotations

import pytest
import torch

from ten_sor_regeneration_gate.storage import (
    CorruptImageStateError,
    ImageNotInitializedError,
    ImageStore,
    ImageStoreError,
    InvalidGateInputError,
)


def image(value: float = 0.25, shape=(1, 8, 9, 3), dtype=torch.float32):
    return torch.full(shape, value, dtype=dtype)


def test_round_trip_is_pixel_shape_and_dtype_exact(tmp_path):
    store = ImageStore(tmp_path)
    original = image(0.125, shape=(2, 7, 11, 4), dtype=torch.float64)

    store.save("carousel-a", 1, original)
    restored = store.load("carousel-a", 1)

    assert restored.shape == original.shape
    assert restored.dtype == original.dtype
    assert torch.equal(restored, original.cpu())


def test_slots_and_sessions_are_isolated(tmp_path):
    store = ImageStore(tmp_path)
    store.save("a", 1, image(0.1))
    store.save("a", 2, image(0.2))
    store.save("b", 1, image(0.3))

    assert torch.equal(store.load("a", 1), image(0.1))
    assert torch.equal(store.load("a", 2), image(0.2))
    assert torch.equal(store.load("b", 1), image(0.3))


def test_persistence_survives_new_store_instance(tmp_path):
    ImageStore(tmp_path).save("persist", 3, image(0.75))
    restored = ImageStore(tmp_path).load("persist", 3)
    assert torch.equal(restored, image(0.75))


def test_missing_slot_has_actionable_error(tmp_path):
    store = ImageStore(tmp_path)
    with pytest.raises(ImageNotInitializedError, match="regenerate to TRUE"):
        store.load("new-session", 1)


def test_corrupt_state_has_actionable_error(tmp_path):
    store = ImageStore(tmp_path)
    path = store.path_for("broken", 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a torch file")

    with pytest.raises(CorruptImageStateError, match="unreadable"):
        store.load("broken", 1)


def test_failed_save_does_not_replace_previous_image(tmp_path, monkeypatch):
    store = ImageStore(tmp_path)
    store.save("safe", 1, image(0.4))

    def fail_save(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(torch, "save", fail_save)
    with pytest.raises(ImageStoreError, match="simulated disk failure"):
        store.save("safe", 1, image(0.9))

    monkeypatch.undo()
    assert torch.equal(store.load("safe", 1), image(0.4))


@pytest.mark.parametrize("session_id", ["", "   ", None, True, "x\x00y"])
def test_invalid_session_ids_are_rejected(tmp_path, session_id):
    with pytest.raises(InvalidGateInputError):
        ImageStore(tmp_path).save(session_id, 1, image())


def test_non_image_tensor_is_rejected(tmp_path):
    with pytest.raises(InvalidGateInputError, match="layout"):
        ImageStore(tmp_path).save("session", 1, torch.zeros((3, 4)))


def test_runtime_files_use_hashed_identifiers(tmp_path):
    store = ImageStore(tmp_path)
    path = store.save("../../outside", "../slot", image())
    assert path.is_relative_to(tmp_path)
    assert ".." not in path.relative_to(tmp_path).parts


def test_fingerprint_changes_on_create_and_replace(tmp_path):
    store = ImageStore(tmp_path)
    before = store.fingerprint("session", 1)
    store.save("session", 1, image(0.1))
    after_create = store.fingerprint("session", 1)
    store.save("session", 1, image(0.2, shape=(1, 9, 9, 3)))
    after_replace = store.fingerprint("session", 1)

    assert before == ("missing",)
    assert after_create[0] == "present"
    assert after_replace[0] == "present"
    assert after_replace != after_create
    assert not any(path.suffix == ".tmp" for path in tmp_path.rglob("*"))
