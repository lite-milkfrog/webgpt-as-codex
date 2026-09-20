# Validation — 简体中文

[English](../validation.md) | **简体中文**

最低 full-system gates：
- repository tests + lint；
- secret scan；
- component manifest schema；
- discovery 不混淆 installed/listening/healthy；
- 每个 enabled local MCP initialize + tools/list；
- Gateway 从每个 enabled backend 列出 namespaced tools；
- core category 至少一个 Gateway safe tool call；
- 启用时验证 OAuth metadata、DCR、PKCE exchange、refresh；
- 启用时 remote edge 可达 OAuth-protected Gateway；
- Manager UI close 不停止 runtime；
- runtime stop/restart 拒绝 unmanaged process 与 stale/reused PID receipt；
- Start All 幂等、preserve healthy unmanaged、无 duplicate；
- process-only system component preserve 但不升级为 protocol health；
- desktop launcher/autostart install/status/uninstall 可逆、无 credential；
- restart/recovery 不依赖 chat memory；
- bootstrap dry-run 幂等；
- tracked 内容无 user-specific secret/private URL；
- README claim 与 verified evidence 一致。
