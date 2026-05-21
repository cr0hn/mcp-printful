"""MCP server — Printful tools."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

# Import printful_cli functions directly (option B: no subprocess overhead)
from printful_cli import api as printful_api
from printful_cli.config import get_token, load_session
from printful_cli.models import (
    DEFAULT_SIZES_ADULTO,
    DEFAULT_SIZES_NINO,
    DEFAULT_SIZES_BEBE,
    PRODUCT_DEFAULTS,
)

# ---------------------------------------------------------------------------
# MCP server — instructions embed the key Printful knowledge
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="mcp-printful",
    instructions="""
You manage Printful products for a WooCommerce store using this MCP.

## Two authentication systems — critical

**Bearer token** (env: PRINTFUL_TOKEN)
- Used for: uploading files to the Printful file library
- Endpoint: api.printful.com
- Set via: `printful-cli config set-token TOKEN` or PRINTFUL_TOKEN env var

**Session cookies** (stored in ~/.config/printful-cli/session.json)
- Used for: saving templates and publishing to WooCommerce
- Obtained via: `printful-cli auth` (opens browser for login)
- If tools return "session expired" or HTTP 403, call `renew_session`

## Product flow

1. `upload_design` → gets a file_id
2. `save_template` → gets a template_id  (uses session)
3. `publish_to_store` → product appears in WooCommerce async ~1-2 min (uses session)

Or use `create_product` for all three steps at once.

## Blueprint restrictions — MUST follow

**BC3001 Adulto (product_id=71)**
- Placement: front_large, template_id=333
- Sizes: XS, S, M, L, XL, 2XL, 3XL, 4XL, 5XL
- Colors: "Black Heather" (dark designs), "White" (light/transparent designs)
- WC categories: camisetas-chico (16) and/or camisetas-chica (17)

**BC3001Y Niño/a (product_id=307)**
- Placement: front, template_id=9
- Sizes: S, M, L, XL ONLY — NO XS, NO 2XL
- Colors: "Black" or "White" — "Black Heather" does NOT exist for this blueprint
- WC category: ONLY camisetas-nino (19) — never mix with chico/chica

**BC3001B Bebé (product_id=305)**
- Placement: front, template_id=55
- Sizes: "6-12m", "12-18m", "18-24m" ONLY — format with dash, only 3 sizes
- Colors: "Black" or "White" — "Black Heather" does NOT exist for this blueprint
- WC category: ONLY camisetas-bebe (18)

## Color selection by design

- Design has dark/complex background → use "Black Heather" (adult) or "Black" (youth/baby)
- Design has white/light/transparent background → use "White"

## Publish is asynchronous

`publish_to_store` returns a task_id. The product appears in WooCommerce
in 1–2 minutes. Use the mcp-woocommerce MCP to verify and update it afterwards
(categories, description, images).

## GET /files listing endpoint is GONE (HTTP 410)

Use `list_files` only for individual lookups. Listing all files requires
calling the Printful dashboard library RPC, not the public API.
""",
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require_token() -> str:
    token = get_token()
    if not token:
        raise RuntimeError(
            "No Printful Bearer token configured. "
            "Set the PRINTFUL_TOKEN environment variable or run: printful-cli config set-token TOKEN"
        )
    return token


def _require_session() -> list[dict]:
    session = load_session()
    if not session:
        raise RuntimeError(
            "No active Printful session. "
            "Run `printful-cli auth` to log in via browser, then retry."
        )
    return session


def _sizes_for_product(product_id: int) -> dict[str, str]:
    return PRODUCT_DEFAULTS.get(product_id, PRODUCT_DEFAULTS[71])["sizes"]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def upload_design(
    url: Annotated[str | None, "Public HTTPS URL of the design image (PNG/JPG). Recommended method."] = None,
    file_path: Annotated[str | None, "Local file path to upload via base64. Less reliable — prefer url."] = None,
) -> dict:
    """
    Upload a design image to the Printful file library.
    Returns a file_id needed for save_template and create_product.
    Prefer url over file_path — base64 uploads sometimes fail processing.
    """
    token = _require_token()
    if not url and not file_path:
        raise ValueError("Provide either url or file_path.")

    if url:
        result = printful_api.upload_file_by_url(url, token=token)
    else:
        result = printful_api.upload_file_local(Path(file_path), token=token)  # type: ignore[arg-type]

    return {
        "file_id": result.id,
        "filename": result.filename,
        "status": result.status,
        "thumbnail_url": result.thumbnail_url,
        "width": result.width,
        "height": result.height,
        "note": "status='waiting' is normal — Printful processes files asynchronously.",
    }


@mcp.tool()
async def get_file_info(
    file_id: Annotated[int, "Printful file ID"],
) -> dict:
    """
    Get details of a Printful file including its thumbnail_url.
    Use this to get the thumbnail_url needed for save_template.
    """
    token = _require_token()
    f = printful_api.get_file_info(file_id, token=token)
    return {
        "file_id": f.id,
        "filename": f.filename,
        "status": f.status,
        "thumbnail_url": f.thumbnail_url,
        "width": f.width,
        "height": f.height,
        "url": f.url,
    }


@mcp.tool()
async def save_template(
    file_id: Annotated[int, "Printful file ID from upload_design"],
    title: Annotated[str, "Product title"],
    color: Annotated[str, "Color name. Adults: 'Black Heather' or 'White'. Youth/Baby: 'Black' or 'White'"],
    product_id: Annotated[int, "Blueprint ID: 71=adulto BC3001, 307=niño BC3001Y, 305=bebé BC3001B"] = 71,
) -> dict:
    """
    Save a Printful design as a product template.
    Requires an active session (run `printful-cli auth` if expired).
    Returns a template_id needed for publish_to_store.
    """
    session = _require_session()
    token = _require_token()
    sizes = _sizes_for_product(product_id)

    result = printful_api.save_template(
        file_id=file_id,
        product_id=product_id,
        color=color,
        sizes=sizes,
        name=title,
        cookies=session,
        token=token,
    )
    return {
        "template_id": result.product_template_id,
        "title": result.title,
        "product_id": result.product_id,
        "next_step": f"Call publish_to_store with template_id={result.product_template_id} and file_id={file_id}",
    }


@mcp.tool()
async def publish_to_store(
    template_id: Annotated[int, "Printful template ID from save_template"],
    file_id: Annotated[int, "Printful file ID from upload_design"],
    title: Annotated[str, "Product title as it will appear in WooCommerce"],
    color: Annotated[str, "Color: adults='Black Heather'/'White', youth/baby='Black'/'White'"],
    product_id: Annotated[int, "Blueprint ID: 71=adulto, 307=niño, 305=bebé"] = 71,
    retail_price: Annotated[float, "Retail price in EUR"] = 14.0,
    description: Annotated[str, "Product description (HTML). Should be macarra, related to the design, ~200 chars min."] = "",
    category_ids: Annotated[
        list[int],
        "WooCommerce category IDs. Adults: [16] chico / [17] chica / [16,17] both. "
        "Youth: [19] ONLY. Baby: [18] ONLY.",
    ] = (),  # type: ignore[assignment]
) -> dict:
    """
    Publish a Printful template to WooCommerce.
    The product appears in WooCommerce asynchronously (1–2 minutes).
    Returns a task_id — use mcp-woocommerce to verify and update the product afterwards.
    """
    session = _require_session()
    token = _require_token()
    sizes = _sizes_for_product(product_id)
    cats = {str(i): str(cid) for i, cid in enumerate(category_ids)} if category_ids else {}

    result = printful_api.publish_template(
        template_id=template_id,
        file_id=file_id,
        product_id=product_id,
        color=color,
        sizes=sizes,
        title=title,
        cookies=session,
        token=token,
        retail_price=retail_price,
        description=description,
        category_ids=cats or None,
    )
    return {
        "task_id": result.task_id,
        "design_id": result.design_id,
        "status": "processing",
        "note": (
            "Product is being generated by Printful (1–2 min). "
            "Use mcp-woocommerce audit_products to verify it appeared, "
            "then update description, categories and images."
        ),
    }


@mcp.tool()
async def create_product(
    design_url: Annotated[str, "Public HTTPS URL of the design PNG/JPG"],
    title: Annotated[str, "Product title"],
    color: Annotated[str, "Color: adults='Black Heather'/'White', youth/baby='Black'/'White'"],
    product_id: Annotated[int, "Blueprint: 71=adulto BC3001, 307=niño BC3001Y, 305=bebé BC3001B"] = 71,
    retail_price: Annotated[float, "Retail price in EUR"] = 14.0,
    description: Annotated[str, "Product description (HTML). Macarra, related to the design, min 200 chars."] = "",
    category_ids: Annotated[
        list[int],
        "WooCommerce category IDs. Adults: [16],[17],[16,17]. Youth: [19] ONLY. Baby: [18] ONLY.",
    ] = (),  # type: ignore[assignment]
) -> dict:
    """
    Full flow: upload design → save template → publish to WooCommerce.
    Convenience wrapper for the three-step process.
    Returns file_id, template_id and task_id.
    """
    session = _require_session()
    token = _require_token()
    sizes = _sizes_for_product(product_id)
    cats = {str(i): str(cid) for i, cid in enumerate(category_ids)} if category_ids else {}

    # Step 1: upload
    pf_file = printful_api.upload_file_by_url(design_url, token=token)

    # Step 2: save template
    template = printful_api.save_template(
        file_id=pf_file.id,
        product_id=product_id,
        color=color,
        sizes=sizes,
        name=title,
        cookies=session,
        token=token,
    )

    # Step 3: publish
    published = printful_api.publish_template(
        template_id=template.product_template_id,
        file_id=pf_file.id,
        product_id=product_id,
        color=color,
        sizes=sizes,
        title=title,
        cookies=session,
        token=token,
        retail_price=retail_price,
        description=description,
        category_ids=cats or None,
    )

    return {
        "file_id": pf_file.id,
        "template_id": template.product_template_id,
        "task_id": published.task_id,
        "status": "processing",
        "note": (
            "Product is being generated by Printful (1–2 min). "
            "Use mcp-woocommerce audit_products to check it appeared and fix categories/description/images."
        ),
    }


@mcp.tool()
async def renew_session() -> dict:
    """
    Check the current Printful session status.
    If expired, instructs the user to run `printful-cli auth` to log in via browser.
    Session is required for save_template, publish_to_store and create_product.
    """
    session = load_session()
    if not session:
        return {
            "status": "expired",
            "action_required": "Run `printful-cli auth` in your terminal to log in via browser.",
        }

    printful_cookies = [c for c in session if "printful.com" in c.get("domain", "")]
    return {
        "status": "active",
        "cookies_count": len(printful_cookies),
        "note": "Session looks active. If Printful calls return HTTP 403, the session may have expired — run `printful-cli auth`.",
    }


@mcp.tool()
async def list_blueprints() -> list[dict]:
    """
    List the supported Printful blueprints (product types) with their restrictions.
    Use this to know which product_id, colors and sizes to use.
    """
    return [
        {
            "product_id": 71,
            "name": "Bella+Canvas 3001 — Adulto Unisex",
            "placement": "front_large",
            "template_id": 333,
            "sizes": list(DEFAULT_SIZES_ADULTO.values()),
            "colors": ["Black Heather (dark designs)", "White (light/transparent designs)"],
            "wc_categories": {"chico": 16, "chica": 17},
            "notes": "Most versatile. Use Black Heather for dark backgrounds, White for light ones.",
        },
        {
            "product_id": 307,
            "name": "Bella+Canvas 3001Y — Niño/a Youth",
            "placement": "front",
            "template_id": 9,
            "sizes": list(DEFAULT_SIZES_NINO.values()),
            "colors": ["Black (dark designs)", "White (light/transparent designs)"],
            "wc_categories": {"nino": 19},
            "notes": "ONLY category 19. 'Black Heather' does NOT exist — use 'Black'. No XS or 2XL.",
        },
        {
            "product_id": 305,
            "name": "Bella+Canvas 3001B — Bebé Infant",
            "placement": "front",
            "template_id": 55,
            "sizes": list(DEFAULT_SIZES_BEBE.values()),
            "colors": ["Black (dark designs)", "White (light/transparent designs)"],
            "wc_categories": {"bebe": 18},
            "notes": "ONLY category 18. 'Black Heather' does NOT exist. Sizes use dash format: '6-12m'.",
        },
    ]
