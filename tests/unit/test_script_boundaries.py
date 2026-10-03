import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sentinel.layers.action.teleporter import SessionState, Teleporter
from sentinel.layers.validation.mutator import Mutation, UIMutator


@pytest.mark.parametrize("strategy", UIMutator.MUTATION_STRATEGIES)
def test_mutation_selector_is_a_script_argument(strategy):
    driver = MagicMock()
    selector = "[data-name=\"O'Reilly\"]'; globalThis.injected = true; //"
    mutation = UIMutator(driver)._apply_fallback_mutation(selector, strategy)
    script, value = driver.execute_script.call_args.args
    assert selector not in script
    assert value == selector
    assert mutation.name != "failed"


@pytest.mark.parametrize("strategy", ["ghost_element", "data_sabotage", "ui_shift"])
@pytest.mark.parametrize("original", ["", "'; globalThis.injected = true; // `${alert(1)}`"])
def test_mutation_restoration_keeps_original_state_as_data(strategy, original):
    driver = MagicMock()
    mutation = Mutation("test", "test", "[data-name=\"O'Reilly\"]", strategy, original)
    assert UIMutator(driver)._revert_fallback_mutation(mutation)
    script, selector, value = driver.execute_script.call_args.args
    assert value == original
    assert selector == mutation.element_selector
    assert "globalThis.injected" not in script


def test_browser_storage_restores_quotes_and_code_as_data(tmp_path):
    driver = MagicMock()
    teleporter = Teleporter(driver, str(tmp_path))
    key = "profile'key"
    value = "'); globalThis.injected = true; //"
    teleporter._apply_state(SessionState([], {key: value}, {key: value}, ""))
    assert driver.execute_script.call_count == 2
    for call in driver.execute_script.call_args_list:
        script, actual_key, actual_value = call.args
        assert (actual_key, actual_value) == (key, value)
        assert value not in script


@pytest.mark.parametrize("name", ["../outside", "..\\outside", "C:outside", "", ".."])
def test_named_state_cannot_escape_directory(tmp_path, name):
    state_dir = tmp_path / "states"
    teleporter = Teleporter(MagicMock(), str(state_dir))
    outside = tmp_path / "outside.json"
    outside.write_text('{"keep": true}')
    with pytest.raises(ValueError):
        teleporter.save_state(name)
    assert not teleporter.restore_state(name)
    assert not teleporter.delete_state(name)
    assert outside.read_text() == '{"keep": true}'


@pytest.fixture
def teleport_backend(monkeypatch):
    calls = []

    class Teleport:
        def __init__(self, driver, file_path):
            self.file_path = file_path
            calls.append(("init", driver, file_path))

        def save(self):
            data = {"metadata": {"source_url": "https://example.com/dashboard"}}
            with open(self.file_path, "w", encoding="utf-8") as output:
                json.dump(data, output)
            calls.append(("save",))
            return data

        def load(self, destination_url):
            calls.append(("load", destination_url))

    monkeypatch.setitem(sys.modules, "selenium_teleport", SimpleNamespace(Teleport=Teleport))
    return calls


def test_teleport_backend_uses_state_path_and_saved_destination(tmp_path, teleport_backend):
    driver = MagicMock()
    teleporter = Teleporter(driver, str(tmp_path))
    expected_path = str(tmp_path / "signed-in.json")
    assert teleporter.save_state("signed-in") == expected_path
    assert teleporter.restore_state("signed-in")
    assert teleport_backend == [
        ("init", driver, expected_path), ("save",),
        ("init", driver, expected_path), ("load", "https://example.com/dashboard"),
    ]


def test_teleport_backend_never_receives_escaping_paths(tmp_path, teleport_backend):
    teleporter = Teleporter(MagicMock(), str(tmp_path))
    with pytest.raises(ValueError):
        teleporter.save_state("../outside")
    assert not teleporter.restore_state("../outside")
    assert teleport_backend == []


def test_legacy_states_restore_when_teleport_is_installed(tmp_path, teleport_backend):
    driver = MagicMock()
    saved = SessionState([], {"key": "value"}, {}, "https://example.com/dashboard")
    (tmp_path / "legacy.json").write_text(json.dumps(saved.to_dict()), encoding="utf-8")
    teleporter = Teleporter(driver, str(tmp_path))
    assert teleporter.restore_state("legacy")
    driver.get.assert_called_once_with(saved.url)
    driver.execute_script.assert_called_once_with(
        "localStorage.setItem(arguments[0], arguments[1]);", "key", "value"
    )
    assert teleport_backend == []


def test_installed_teleport_public_interface(tmp_path, monkeypatch):
    context = pytest.importorskip("selenium_teleport.context")
    driver = MagicMock()
    expected_path = str(tmp_path / "session.json")
    destination = "https://example.com/dashboard"

    def save_state(actual_driver, file_path, **kwargs):
        assert actual_driver is driver
        assert file_path == expected_path
        data = {"metadata": {"source_url": destination}}
        (tmp_path / "session.json").write_text(json.dumps(data), encoding="utf-8")
        return data

    load_state = MagicMock(return_value={})
    monkeypatch.setattr(context, "save_state", save_state)
    monkeypatch.setattr(context, "load_state", load_state)
    teleporter = Teleporter(driver, str(tmp_path))
    assert teleporter.save_state("session") == expected_path
    assert teleporter.restore_state("session")
    assert load_state.call_args.args == (driver, expected_path, destination)
