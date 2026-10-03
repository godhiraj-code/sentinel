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
