from __future__ import annotations

import pytest
import torch

import ten_sor_regeneration_gate as package
from ten_sor_regeneration_gate.regeneration_gate import TenSorRegenerationGate
from ten_sor_regeneration_gate.storage import (
    ImageNotInitializedError,
    ImageStore,
    InvalidGateInputError,
)


def image(value: float):
    return torch.full((1, 5, 6, 3), value, dtype=torch.float32)


def test_input_declares_fresh_image_lazy():
    config = TenSorRegenerationGate.INPUT_TYPES()["required"]
    assert config["fresh_image"][1]["lazy"] is True
    assert config["regenerate"][1]["default"] is True


def test_regenerate_requests_lazy_image_only_when_missing(tmp_path):
    gate = TenSorRegenerationGate(ImageStore(tmp_path))
    assert gate.check_lazy_status(True, "session", 1, None) == ["fresh_image"]
    assert gate.check_lazy_status(True, "session", 1, image(0.1)) == []


def test_preserve_never_requests_lazy_image(tmp_path):
    gate = TenSorRegenerationGate(ImageStore(tmp_path))
    assert gate.check_lazy_status(False, "session", 1, None) == []


def test_first_generation_stores_and_returns_original_tensor(tmp_path):
    store = ImageStore(tmp_path)
    gate = TenSorRegenerationGate(store)
    fresh = image(0.1)

    output = gate.execute(True, "session", 1, fresh)[0]

    assert output is fresh
    assert torch.equal(store.load("session", 1), fresh)


def test_partial_regeneration_keeps_locked_slots(tmp_path):
    store = ImageStore(tmp_path)
    gates = [TenSorRegenerationGate(store) for _ in range(4)]
    initial = [image(0.1), image(0.2), image(0.3), image(0.4)]
    for slot, (gate, tensor) in enumerate(zip(gates, initial), start=1):
        gate.execute(True, "carousel", slot, tensor)

    incoming = [image(0.5), image(0.6), image(0.7), image(0.8)]
    outputs = [
        gates[0].execute(False, "carousel", 1, None)[0],
        gates[1].execute(False, "carousel", 2, None)[0],
        gates[2].execute(True, "carousel", 3, incoming[2])[0],
        gates[3].execute(True, "carousel", 4, incoming[3])[0],
    ]

    assert torch.equal(outputs[0], initial[0])
    assert torch.equal(outputs[1], initial[1])
    assert torch.equal(outputs[2], incoming[2])
    assert torch.equal(outputs[3], incoming[3])


def test_unlocking_replaces_stored_image(tmp_path):
    store = ImageStore(tmp_path)
    gate = TenSorRegenerationGate(store)
    gate.execute(True, "carousel", 1, image(0.1))
    gate.execute(True, "carousel", 1, image(0.9))
    assert torch.equal(store.load("carousel", 1), image(0.9))


def test_locked_uninitialized_slot_errors_without_fresh_image(tmp_path):
    gate = TenSorRegenerationGate(ImageStore(tmp_path))
    with pytest.raises(ImageNotInitializedError, match="run this slot once"):
        gate.execute(False, "new", 1, None)


def test_regenerate_without_resolved_lazy_input_errors(tmp_path):
    gate = TenSorRegenerationGate(ImageStore(tmp_path))
    with pytest.raises(InvalidGateInputError, match="was not evaluated"):
        gate.execute(True, "session", 1, None)


def test_node_registration():
    assert package.NODE_CLASS_MAPPINGS["10SORRegenerationGate"].FUNCTION == "execute"
