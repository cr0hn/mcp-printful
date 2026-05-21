"""Shared fixtures and pytest configuration."""
from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end tests that require real Printful credentials")


def pytest_collection_modifyitems(config, items):
    run_e2e = config.getoption("--e2e", default=False)
    skip_e2e = pytest.mark.skip(reason="E2E tests require --e2e flag and real Printful credentials")
    for item in items:
        if "e2e" in item.keywords and not run_e2e:
            item.add_marker(skip_e2e)


def pytest_addoption(parser):
    parser.addoption("--e2e", action="store_true", default=False, help="Run E2E tests against real Printful")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_file():
    from printful_cli.models import PrintfulFile
    return PrintfulFile(
        id=991079282,
        type="default",
        hash="abc123",
        url="https://example.com/design.png",
        filename="design.png",
        mime_type="image/png",
        size=500000,
        width=1200,
        height=1200,
        status="ok",
        created=1700000000,
        visible=True,
        thumbnail_url="https://files.cdn.printful.com/files/abc/abc123_thumb.png",
    )


@pytest.fixture
def mock_template():
    from printful_cli.models import ProductTemplate
    t = ProductTemplate(
        product_template_id=102850926,
        title="Test Product",
        product_id=71,
        colors={"Black Heather": "#0b0b0b"},
        sizes={"0": "XS", "1": "S"},
    )
    t.file_id = 991079282
    return t


@pytest.fixture
def mock_publish_result():
    from printful_cli.models import PublishResult
    return PublishResult(
        sync_product_id=None,
        task_id=923079350,
        task_pusher_key="generator-task-abc",
        design_id=389168298,
    )


@pytest.fixture
def mock_session():
    return [
        {"name": "_session", "value": "fake_session", "domain": "www.printful.com"},
        {"name": "_csrf", "value": "fake_csrf", "domain": "www.printful.com"},
    ]
