"""Unit tests for MCP Printful server tools."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# upload_design
# ---------------------------------------------------------------------------

async def test_upload_design_by_url_success(mock_file):
    with (
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.upload_file_by_url", return_value=mock_file),
    ):
        from mcp_printful.server import upload_design
        result = await upload_design(url="https://example.com/design.png")

    assert result["file_id"] == 991079282
    assert result["filename"] == "design.png"
    assert result["status"] == "ok"
    assert result["thumbnail_url"] is not None
    assert "note" in result


async def test_upload_design_by_path_success(mock_file, tmp_path):
    fake_file = tmp_path / "design.png"
    fake_file.write_bytes(b"PNG")

    with (
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.upload_file_local", return_value=mock_file),
    ):
        from mcp_printful.server import upload_design
        result = await upload_design(file_path=str(fake_file))

    assert result["file_id"] == 991079282


async def test_upload_design_no_args_raises():
    from mcp_printful.server import upload_design
    with pytest.raises(ValueError, match="url or file_path"):
        await upload_design()


async def test_upload_design_missing_token():
    with patch("mcp_printful.server.get_token", return_value=None):
        from mcp_printful.server import upload_design
        # Reload to pick up the mock
        import importlib
        import mcp_printful.server as srv
        importlib.reload(srv)

    with patch("mcp_printful.server._require_token", side_effect=RuntimeError("No token")):
        from mcp_printful.server import upload_design
        with pytest.raises(RuntimeError, match="No token"):
            await upload_design(url="https://example.com/design.png")


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------

async def test_get_file_info_returns_details(mock_file):
    with (
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.get_file_info", return_value=mock_file),
    ):
        from mcp_printful.server import get_file_info
        result = await get_file_info(file_id=991079282)

    assert result["file_id"] == 991079282
    assert result["thumbnail_url"] is not None
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# save_template
# ---------------------------------------------------------------------------

async def test_save_template_adulto(mock_template, mock_session):
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.save_template", return_value=mock_template),
    ):
        from mcp_printful.server import save_template
        result = await save_template(
            file_id=991079282,
            title="Test Product",
            color="Black Heather",
            product_id=71,
        )

    assert result["template_id"] == 102850926
    assert result["product_id"] == 71
    assert "next_step" in result


async def test_save_template_nino(mock_template, mock_session):
    mock_template.product_id = 307
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.save_template", return_value=mock_template) as mock_save,
    ):
        from mcp_printful.server import save_template
        await save_template(file_id=991079282, title="Test Niño", color="Black", product_id=307)

    # Verify niño sizes were used (S,M,L,XL — no XS)
    call_kwargs = mock_save.call_args.kwargs
    assert "XS" not in call_kwargs["sizes"].values()
    assert "S" in call_kwargs["sizes"].values()


async def test_save_template_bebe(mock_template, mock_session):
    mock_template.product_id = 305
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.save_template", return_value=mock_template) as mock_save,
    ):
        from mcp_printful.server import save_template
        await save_template(file_id=991079282, title="Test Bebé", color="Black", product_id=305)

    call_kwargs = mock_save.call_args.kwargs
    sizes_values = list(call_kwargs["sizes"].values())
    assert all("-" in s for s in sizes_values), f"Bebé sizes must use dash format: {sizes_values}"


async def test_save_template_expired_session():
    with patch("mcp_printful.server._require_session", side_effect=RuntimeError("No session")):
        from mcp_printful.server import save_template
        with pytest.raises(RuntimeError, match="No session"):
            await save_template(file_id=1, title="T", color="Black")


# ---------------------------------------------------------------------------
# publish_to_store
# ---------------------------------------------------------------------------

async def test_publish_to_store_returns_task_id(mock_publish_result, mock_session):
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.publish_template", return_value=mock_publish_result),
    ):
        from mcp_printful.server import publish_to_store
        result = await publish_to_store(
            template_id=102850926,
            file_id=991079282,
            title="Test",
            color="Black Heather",
            category_ids=[16],
        )

    assert result["task_id"] == 923079350
    assert result["status"] == "processing"
    assert "note" in result


async def test_publish_to_store_without_categories(mock_publish_result, mock_session):
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.publish_template", return_value=mock_publish_result) as mock_pub,
    ):
        from mcp_printful.server import publish_to_store
        await publish_to_store(template_id=1, file_id=1, title="T", color="White")

    call_kwargs = mock_pub.call_args.kwargs
    assert call_kwargs["category_ids"] is None


# ---------------------------------------------------------------------------
# create_product (full flow)
# ---------------------------------------------------------------------------

async def test_create_product_calls_all_three_steps(
    mock_file, mock_template, mock_publish_result, mock_session
):
    with (
        patch("mcp_printful.server._require_session", return_value=mock_session),
        patch("mcp_printful.server._require_token", return_value="tk_test"),
        patch("mcp_printful.server.printful_api.upload_file_by_url", return_value=mock_file) as up,
        patch("mcp_printful.server.printful_api.save_template", return_value=mock_template) as save,
        patch("mcp_printful.server.printful_api.publish_template", return_value=mock_publish_result) as pub,
    ):
        from mcp_printful.server import create_product
        result = await create_product(
            design_url="https://example.com/design.png",
            title="Full Flow Product",
            color="Black Heather",
            product_id=71,
            retail_price=14.0,
            description="<p>Test description that is long enough.</p>",
            category_ids=[16],
        )

    assert up.called
    assert save.called
    assert pub.called
    assert result["file_id"] == 991079282
    assert result["template_id"] == 102850926
    assert result["task_id"] == 923079350


# ---------------------------------------------------------------------------
# renew_session
# ---------------------------------------------------------------------------

async def test_renew_session_active(mock_session):
    with patch("mcp_printful.server.load_session", return_value=mock_session):
        from mcp_printful.server import renew_session
        result = await renew_session()

    assert result["status"] == "active"
    assert result["cookies_count"] == 2


async def test_renew_session_expired():
    with patch("mcp_printful.server.load_session", return_value=None):
        from mcp_printful.server import renew_session
        result = await renew_session()

    assert result["status"] == "expired"
    assert "printful-cli auth" in result["action_required"]


# ---------------------------------------------------------------------------
# list_blueprints
# ---------------------------------------------------------------------------

async def test_list_blueprints_returns_all_three():
    from mcp_printful.server import list_blueprints
    result = await list_blueprints()

    assert len(result) == 3
    ids = {b["product_id"] for b in result}
    assert ids == {71, 307, 305}


async def test_list_blueprints_nino_has_no_xs():
    from mcp_printful.server import list_blueprints
    result = await list_blueprints()
    nino = next(b for b in result if b["product_id"] == 307)
    assert "XS" not in nino["sizes"]
    assert "S" in nino["sizes"]


async def test_list_blueprints_bebe_sizes_use_dash_format():
    from mcp_printful.server import list_blueprints
    result = await list_blueprints()
    bebe = next(b for b in result if b["product_id"] == 305)
    assert all("-" in s for s in bebe["sizes"])


async def test_list_blueprints_color_restrictions():
    from mcp_printful.server import list_blueprints
    result = await list_blueprints()
    adulto = next(b for b in result if b["product_id"] == 71)
    nino = next(b for b in result if b["product_id"] == 307)
    # Adult has Black Heather, youth uses Black
    assert any("Black Heather" in c for c in adulto["colors"])
    assert not any("Black Heather" in c for c in nino["colors"])
    assert any("Black" in c for c in nino["colors"])
