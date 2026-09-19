"""Mark every test in this directory as an opt-in live integration test."""

import pytest


def pytest_collection_modifyitems(items):
    integration_marker = pytest.mark.integration
    for item in items:
        if item.path.parent == item.config.rootpath / "tests" / "integration":
            item.add_marker(integration_marker)
