# Translation Coverage Contract / 翻译覆盖契约

本文件定义 Stage18 的可回归双语规则。机器可读事实位于 `docs/TRANSLATION-COVERAGE.json`。

## Mirror convention / 镜像约定

- 根目录人类入口：英文原文件 + 同级 `*.zh-CN.md`，例如 `README.md` -> `README.zh-CN.md`。
- 当前 live docs：`docs/<NAME>.md` -> `docs/zh-CN/<NAME>.md`。
- Product Skill/Guide：`skills/webgpt-as-codex/<PATH>.md` -> `skills/webgpt-as-codex/zh-CN/<PATH>.md`。
- Manager：`manager/static/index.html` 与 `index.zh-CN.html` 是语言 shell，继续共享 `manager.js` / `manager.css`。
- `LICENSE` 永远保留原始英文 legal text；`LICENSE.zh-CN.md` 只是非约束性阅读译本。
- 历史 closure/evidence/prompt 是 canonical evidence，不为了视觉统一而改写。它们通过本 manifest 和 `docs/zh-CN/HISTORICAL-EVIDENCE-INDEX.md` 获得明确中文处理。
- Python/JavaScript/CSS/tests/scripts/component JSON/TOML 中的协议键、命令、URL、schema key、hash、identifier 不做机械翻译；manifest 必须说明为何属于语言中立、机器内容或历史证据。

## Status / 状态

- `MIRRORED_CURRENT`：当前英文人类可读来源有完整中文镜像。
- `MIRROR_TARGET`：该文件本身就是某一英文来源的中文镜像。
- `BILINGUAL_INLINE`：同一文件已提供中英双语契约。
- `LANGUAGE_NEUTRAL`：文本文件存在，但语义主要是代码/协议/机器配置，不应翻译。
- `LEGAL_ORIGINAL_PRESERVED`：法律原文必须逐字节保留，并通过独立非约束译本提供中文阅读。
- `HISTORICAL_EVIDENCE_PRESERVED_WITH_INDEX`：历史证据原样保留，并由中文索引解释其用途/边界。
- `NOT_HUMAN_READER_CONTENT`：虽然格式是文本，但它不是面向读者的自然语言文档。
- `LOCALIZED_OPERATIONAL_PROFILE`：当前 portable operational Skill 保留其已验证的中文优先/中英混合工作形态；技术 identifier 精确保留，machine-local overlay 不进入发行版。该状态用于 canonical `skills/computer-agent/` release tree。

## Regression gate / 回归门禁

`tests/test_stage18.py` 检查：
1. 每一个 tracked/untracked 候选文本文件都有显式 disposition，或受声明的 dynamic historical/current Skill 规则覆盖；
2. `MIRRORED_CURRENT` 的 mirror 路径真实存在；
3. 原始 `LICENSE` SHA-256 保持 Stage18 基线值；
4. component manifests 与第三方 provenance 一致；
5. `pyproject.toml` 的 build/runtime/dev dependency 都被 provenance 覆盖；
6. release package resources 包含双语 README、legal/notices 与 coverage manifest。

中文镜像是阅读体验，不创建第二套协议或运行时真相。遇到技术 identifier、路径、命令、URL、schema key、hash 或代码块时，应保留原值。
