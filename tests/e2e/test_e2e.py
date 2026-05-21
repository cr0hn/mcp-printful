"""
End-to-end tests against real Printful + WooCommerce.

Requires:
  - PRINTFUL_TOKEN env var set
  - ~/.config/printful-cli/session.json exists (run printful-cli auth first)
  - Run with: pytest --e2e tests/e2e/

Uses a public test image — no real design is stored permanently.
"""
from __future__ import annotations

import os
import pytest

pytestmark = pytest.mark.e2e

TEST_DESIGN_URL = "https://files.cdn.printful.com/upload/product-catalog-img/2c/2cbb9851b454bbf9e642644447bc11c1_l"
TEST_TITLE = "[MCP-E2E-TEST] Delete me"


@pytest.fixture
def has_credentials() -> bool:
    token = os.environ.get("PRINTFUL_TOKEN", "")
    from printful_cli.config import load_session
    session = load_session()
    return bool(token) and bool(session)


async def test_e2e_renew_session_reports_status():
    from mcp_printful.server import renew_session
    result = await renew_session()
    assert result["status"] in ("active", "expired")
    if result["status"] == "expired":
        pytest.skip("Session expired — run printful-cli auth first")


async def test_e2e_list_blueprints():
    from mcp_printful.server import list_blueprints
    result = await list_blueprints()
    assert len(result) == 3
    assert all(b["product_id"] in (71, 307, 305) for b in result)


async def test_e2e_upload_design():
    from mcp_printful.server import upload_design
    result = await upload_design(url=TEST_DESIGN_URL)
    assert "file_id" in result
    assert result["file_id"] > 0
    # Store for downstream tests
    pytest.e2e_file_id = result["file_id"]


async def test_e2e_get_file_info():
    if not hasattr(pytest, "e2e_file_id"):
        pytest.skip("Requires test_e2e_upload_design to run first")
    from mcp_printful.server import get_file_info
    result = await get_file_info(file_id=pytest.e2e_file_id)
    assert result["file_id"] == pytest.e2e_file_id
    assert result["status"] in ("ok", "waiting")


async def test_e2e_save_template():
    if not hasattr(pytest, "e2e_file_id"):
        pytest.skip("Requires test_e2e_upload_design to run first")
    from mcp_printful.server import save_template
    result = await save_template(
        file_id=pytest.e2e_file_id,
        title=TEST_TITLE,
        color="Black Heather",
        product_id=71,
    )
    assert "template_id" in result
    assert result["template_id"] > 0
    pytest.e2e_template_id = result["template_id"]


async def test_e2e_full_create_product_nino():
    """Full flow for BC3001Y niño — verifies blueprint restrictions work end-to-end."""
    from mcp_printful.server import create_product
    result = await create_product(
        design_url=TEST_DESIGN_URL,
        title=f"{TEST_TITLE} Niño",
        color="Black",  # not "Black Heather" — would fail for BC3001Y
        product_id=307,
        retail_price=14.0,
        category_ids=[19],
    )
    assert result["task_id"] is not None
    assert result["status"] == "processing"
