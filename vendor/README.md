# Vendored derivative sources

This directory contains complete source snapshots only for third-party components that WebGPT-as-Codex has materially modified and must reproduce on a fresh deployment.

## coding-tools-mcp

- Upstream: https://github.com/xyTom/coding-tools-mcp
- Base commit: bedb632e1afd2e9ec9b268a50fe0b04695c22c64
- License: Apache-2.0
- Complete tracked source snapshot: `vendor/coding-tools-mcp/`
- Upstream `LICENSE` and `NOTICE` are retained.
- `WAC_MODIFICATIONS.md` and `WAC_UPSTREAM_DIFF.patch` record the derivative delta.

## serena-agent

- Upstream: https://github.com/oraios/serena
- Source ref: v1.7.0 / 949a27ef1e5fda1a6e7b561e777bcece345c6ffd
- License: MIT for the complete historical v1.7.0 application release
- Complete source snapshot: `vendor/serena-agent/`
- The verified WAC `find_implementations` fallback is included.
- `WAC_MODIFICATIONS.md` and `WAC_UPSTREAM_DIFF.patch` record the derivative delta.

Playwright is intentionally not fully vendored: WAC installs the official package and deterministically reapplies `src/webgpt_as_codex/playwright_hotfix.py`.

Remote Desktop Commander is not vendored because WAC did not modify its proprietary hosted relay source. WAC only owns its local integration/recovery code.

The Git source checkout is the canonical fresh-machine deployment artifact for these derivatives; the current thin Python wheel alone is not a complete bundled-source deployment.