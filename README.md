# mcp-printful

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

**MCP server for Printful product management.** Gives Claude direct access to Printful — upload designs, save templates and publish products to WooCommerce without writing scripts.

Built on top of [printful-cli](https://github.com/cr0hn/prinful-cli), which is installed automatically as a dependency — no separate setup needed. For WooCommerce management after publishing (categories, descriptions, images) use [mcp-woocommerce](https://github.com/cr0hn/mcp-woocommerce).

---

## What it does

| Tool | Description |
|---|---|
| `upload_design` | Upload a design image to Printful file library (by URL or local file) |
| `get_file_info` | Get details of an uploaded file including thumbnail_url |
| `save_template` | Save a design as a Printful product template |
| `publish_to_store` | Publish a saved template to WooCommerce |
| `create_product` | Full flow: upload → save template → publish (one call) |
| `renew_session` | Check session status / instruct user to re-authenticate |
| `list_blueprints` | Show supported product types with their restrictions |

---

## Installation

Installing `mcp-printful` also installs `printful-cli` automatically — no separate step needed.

```bash
# Run directly with uvx (no install required)
uvx --from git+https://github.com/cr0hn/mcp-printful mcp-printful

# Or install permanently
uv tool install git+https://github.com/cr0hn/mcp-printful
```

### First-time setup

After installing, configure your credentials once:

```bash
# Bearer token — for file uploads (get it at developers.printful.com/tokens)
printful-cli config set-token YOUR_TOKEN

# WooCommerce store ID
printful-cli config set-store YOUR_STORE_ID

# Browser login — for saving templates and publishing (opens browser)
printful-cli auth
```

These are stored in `~/.config/printful-cli/` and shared between the CLI and the MCP.

---

## Configuration

| Variable | Description | Required |
|---|---|---|
| `PRINTFUL_TOKEN` | Printful Developer Portal Bearer token | For `upload_design`, `get_file_info` |

Session cookies are read from `~/.config/printful-cli/session.json` (set by `printful-cli auth`).

---

## Claude Desktop setup

```json
{
  "mcpServers": {
    "printful": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/cr0hn/mcp-printful", "mcp-printful"],
      "env": {
        "PRINTFUL_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add printful \
  --command uvx \
  --args "--from,git+https://github.com/cr0hn/mcp-printful,mcp-printful" \
  -e PRINTFUL_TOKEN=your_token_here
```

---

## Supported blueprints

| Product | product_id | Sizes | Colors | WC category |
|---|---|---|---|---|
| BC3001 Adulto Unisex | 71 | XS–5XL | `"Black Heather"` / `"White"` | chico (16), chica (17) |
| BC3001Y Niño/a | 307 | S, M, L, XL | `"Black"` / `"White"` | **niño (19) ONLY** |
| BC3001B Bebé | 305 | 6-12m, 12-18m, 18-24m | `"Black"` / `"White"` | **bebé (18) ONLY** |

> ⚠️ `"Black Heather"` does NOT exist for BC3001Y or BC3001B — use `"Black"`.

---

## Product flow

```
1. upload_design(url)  →  file_id
2. save_template(file_id, title, color, product_id)  →  template_id
3. publish_to_store(template_id, file_id, ...)  →  task_id

# Or all at once:
create_product(design_url, title, color, product_id, ...)  →  {file_id, template_id, task_id}
```

After publishing, use **mcp-woocommerce** to verify the product appeared and update categories, description and images.

---

## Development

```bash
uv sync --all-groups
uv run pytest

# E2E (requires real credentials)
PRINTFUL_TOKEN=... uv run pytest --e2e tests/e2e/ -v
```

---

## License

MIT
