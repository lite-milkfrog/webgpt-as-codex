# WebGPT-as-Codex derivative snapshot

Upstream: https://github.com/oraios/serena
Upstream tag: v1.7.0
Upstream tag commit: 949a27ef1e5fda1a6e7b561e777bcece345c6ffd
License: MIT (v1.7.0 is the last MIT-licensed Serena release)
Snapshot policy: complete v1.7.0 source with the verified WebGPT-as-Codex implementation fallback applied.

Modified relative to upstream:
- src/serena/tools/symbol_tools.py

Change purpose:
- Preserve a deterministic exact-name-and-kind implementation fallback when the language backend does not return implementations directly.
- Live acceptance resolved Base/value to Child/value with implementation_fallback=exact-name-and-kind.

WAC_UPSTREAM_DIFF.patch records the exact derivative delta.
