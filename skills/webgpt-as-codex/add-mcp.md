# Add MCP Workflow

1. Identify upstream source, license, install method and supported transport.
2. Create a public-safe component manifest with no credentials.
3. Discover before install; do not reinstall a healthy compatible instance.
4. Start/bind to loopback by default.
5. Validate initialize, tools/list and one safe call when possible.
6. Register the server in the gateway using a stable component id.
7. Add it to a curated Tool Group only if its tools improve the intended agent role.
8. Add Skill routing only for unique or meaningfully better capability.
9. Add Manager/Doctor visibility and repair hints.
10. Record version evidence and any machine-specific caveat outside portable Skill rules.

Secrets are environment/credential-store references, never manifest literals.
