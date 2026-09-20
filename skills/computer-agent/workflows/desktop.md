# Desktop GUI Workflow

## 适用

Windows 设置、原生软件、系统弹窗、无 CLI/API 的桌面操作。

涉及 Qt / Electron / canvas / 自绘控件、高 DPI、视觉坐标点击时，额外读取：

如果任务是“在已登录微信里把本地文件发到文件传输助手”，直接读取 `workflows/wechat-file-transfer.md`。该任务不要从通用坐标点击流程重新摸索。
`workflows/windows-gui-visual-calibration.md`。

### 微信 / QQ 硬规则

- 微信、QQ 的业务状态核对 **Screenshot-only**：只用当前截图/原图确认“当前聊天是谁、附件是否挂上、发送是否成功、消息/文件卡片是否出现”。
- UI Tree/UIA 只能辅助窗口、焦点、标题等元数据；不得因为 UIA 缺元素就推翻截图事实。
- 如果 Screenshot 与 UI Tree 冲突，Screenshot 胜出。
- 优先保存并查看 Windows-MCP 原始 Screenshot；不要只看 Snapshot 文本树。

## 先问：能否不用 GUI？

如果任务能通过稳定的 API/CLI/文件操作完成，优先 Desktop Commander 或专用 MCP。GUI 是最后的交互层，不是默认层。

但当用户目标本身就是桌面 GUI 交互，且应用已有明确原生控件时，应优先操作该原生控件，不要为了“绕 GUI”额外制造脚本、helper window、OCR 或 CLI workaround。

## Windows-MCP 安全循环

`Observe → Locate → Convert(if needed) → Act → Verify → Classify → Recover`

### Observe

Snapshot 当前窗口、焦点、可交互元素。界面有变化就重新 Observe。

### Locate

优先：

1. UIA label / 控件
2. 键盘快捷键
3. 当前实时 Screenshot 的视觉定位
4. 绝对坐标

### Convert

如果 Screenshot metadata 返回 `Screenshot Coordinate Scale != 1` 或非零 `Screenshot Region`，先按
`workflows/windows-gui-visual-calibration.md`
转换截图坐标到真实屏幕坐标。

不要把 Windows DPI scale 和 Screenshot downscale 当成同一比例，也不要直接拿用户上传截图的像素坐标调用 `Click`。

### Act

一次执行一个有意义动作。不要从一个旧 Snapshot 连续盲点多个按钮。

### Verify

操作后重新 Snapshot/读取窗口状态，确认目标真的发生。

`Click` 返回成功只说明输入事件被注入，不等于业务动作成功。

若预期后态没被检测到，先判断：

- `ACTION_FAILURE`：动作真的没发生；
- `OBSERVER_FAILURE`：动作已经发生，但观察规则太窄，例如只认 `#32770`，漏掉 Qt `选择文件`；
- `FOCUS_FAILURE`：输入发给了错误窗口；
- `DIALOG_LAYER_CHANGED`：已经进入下一层 modal/file chooser；
- `INPUT_ERROR`：路径/编码/转义错误。

不要把所有失败都归因到“坐标不准”。

## 当前高 DPI 设备规则

本机环境事实读取 `environment.local.md`。

已验证：

- Windows-MCP 本身为 Per-Monitor DPI Aware。
- DPI awareness 不代表返回给模型的 Screenshot 一定是原始像素尺寸。
- Screenshot 可能为了传输效率再次 downscale，并返回独立的 `Screenshot Coordinate Scale`。
- 错点一次后停止，重新观察、重新定位、重新转换；不得连续试点“找位置”。

## 窗口管理

- 目标应用：bring-to-front / focus / restore。
- 用户原本已经打开的其它窗口不要随便关闭；需要腾位置时优先最小化、切后台、移动或 Snap。
- 只有用户明确要求关闭，或窗口明确由当前 Agent 临时创建且关闭不会影响用户状态时，才允许 Close / Alt+F4。
- 不要为了拖拽上传先关闭用户已有窗口。

## 输入

对文本框优先 UI 元素定位或 Tab 导航。长文本应使用工具可靠的粘贴路径（如果实现支持），避免高频逐键丢字符。

文件路径/命令文本必须区分“程序字符串转义”和“GUI 中真实文本”。Windows 文件选择器需要普通路径，不得把 JSON/PowerShell 中的双反斜杠表示原样输入。

## 原生 GUI 优先

如果当前应用已经有明确的“添加文件 / 打开 / 上传 / 保存”控件：

1. 先用原生控件；
2. 每一步观察后态；
3. 只有原生路径有证据证明不可用时，才降级到剪贴板文件粘贴、拖拽、helper window 或 CLI workaround。

详细失败树与微信上传回归案例见 `workflows/windows-gui-visual-calibration.md`。

## 原生确认按钮

涉及安装、删除、授权、发送或系统设置时按 P2/P3。
