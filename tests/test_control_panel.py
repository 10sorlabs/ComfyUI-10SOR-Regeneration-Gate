from __future__ import annotations

import json

import pytest

import ten_sor_regeneration_gate as package
from ten_sor_regeneration_gate.control_panel import (
    MAX_CONTROL_SLOTS,
    TenSorRegenerationControlPanel,
)


def test_backend_registration():
    assert package.NODE_CLASS_MAPPINGS["10SORRegenerationControlPanel"] is TenSorRegenerationControlPanel
    assert package.WEB_DIRECTORY == "./web"


def test_has_many_native_subgraph_compatible_outputs():
    assert len(TenSorRegenerationControlPanel.RETURN_TYPES) == MAX_CONTROL_SLOTS
    assert MAX_CONTROL_SLOTS >= 1024
    assert set(TenSorRegenerationControlPanel.RETURN_TYPES) == {"BOOLEAN"}


def test_enabled_by_default_and_individual_overrides():
    result = TenSorRegenerationControlPanel().execute(json.dumps([True, False, True]))
    assert result[:4] == (True, False, True, True)
    assert len(result) == MAX_CONTROL_SLOTS


def test_disable_all():
    result = TenSorRegenerationControlPanel().execute(json.dumps([False] * 24))
    assert result[:24] == (False,) * 24
    assert result[24] is True


@pytest.mark.parametrize("bad", ["not-json", "null", "{}", "[true, 0]", "[1]", "[] trailing"])
def test_invalid_state_rejected(bad):
    with pytest.raises(ValueError):
        TenSorRegenerationControlPanel().execute(bad)
