# Windows GUI Visual Calibration & Execution Lessons

> 适用于 Windows-MCP 操作 Qt / Electron / canvas / 自绘桌面 UI、高 DPI、多显示器、截图下采样、系统文件选择器、拖拽/上传、复杂焦点与多层弹窗。
>
> 本模块由 2026-09-19 微信“文件传输助手上传 ZIP”真实失败链路沉淀。目标不是记住某个坐标，而是让后续 Agent 在类似 GUI 场景中做到：**先看、再定位、只做一步、马上验证；遇到失败先分清“动作失败”还是“观察失败”。**

## 微信 / QQ：Screenshot-only 验收硬规则

微信、QQ 这类 Qt / 自绘客户端大概率不会完整暴露 UI Tree/UIA。对这两类应用：

- **业务状态核对只允许使用 Screenshot / 原图视觉证据**；
- UI Tree/UIA 最多辅助窗口句柄、窗口标题、焦点、前台状态，不允许用来判定控件/附件/消息“存在或不存在”；
- `FOUND=0`、tree 缺节点、role 缺失都不能触发重试或回滚；
- Screenshot 与 UI Tree 冲突时，Screenshot 胜出；
- 优先读取 Windows-MCP 返回的原始/最高分辨率 Screenshot，而不是只看 Snapshot 文本；
- 用户上传的清晰原图可以确认当前语义状态，但点击坐标仍应来自当前 live Screenshot / 当前窗口几何。

这条规则是微信、QQ 的强制例外，不沿用通用“UIA label 优先”作为验收标准。

## 0. 一句话结论

Windows-MCP 的核心不是“猜坐标点鼠标”，而是：

`Observe -> Locate -> Convert -> Act -> Verify -> Classify -> Recover -> Continue -> Learn`

其中最容易出错的不是“能不能点”，而是：

- 用错坐标空间；
- UIA 看不到自绘控件；
- 目标窗口没拿到前台；
- 动作其实成功了，但后态检测规则太窄，误判成失败；
- 弹窗发生了层级切换；
- 路径/文本输入被转义坏；
- 把“工具调用成功”误报成“业务目标完成”；
- 为了绕过一个简单原生控件，过早制造 helper window / OCR / CLI / 拖拽 workaround。

---

# 1. 微观标准案例：微信文件传输助手上传 ZIP

这一流程是 Windows-MCP GUI 自动化的标准回归案例。

目标：

> 在已经登录的微信 PC 客户端中，把一个本地 ZIP 发到“文件传输助手”。

## 1.1 前置条件

操作前确认：

- 目标文件真实存在；
- 目标聊天明确是“文件传输助手”；
- 用户已明确要求发送，因此发送动作在授权范围内；
- 微信窗口已打开；
- **如果微信已经登录且已有运行中的主窗口，优先接管现有实例，禁止从开始菜单/快捷方式再次启动微信。** 重新启动可能只拉起登录页、升级提示页或第二个 Qt wrapper，造成“看起来没登录”的假状态；
- 接管顺序：先枚举现有 微信 / Weixin / WeChat 顶层窗口与任务栏运行实例 → restore/bring-to-front 已登录主窗口 → Snapshot/Screenshot 识别当前聊天状态；只有确认没有可用已登录会话时，才走登录/启动 fallback；
- 若同时出现登录页与已登录主窗口，登录页属于错误分支/辅助窗口，不能把它当作“微信未登录”的证据；应保留用户主窗口并切回现有登录会话；
- 用户已有其它窗口默认保留，不为了方便随意关闭；
- 文件名/路径按文件系统真实文本处理，不提前加额外转义。

对于本次真实案例：

- ZIP：`JARVIS-3.0.0-手机安装三件套.zip`
- Windows 路径应是正常单反斜杠文本，例如：
  `C:\Users\24734\Desktop\JARVIS-3.0.0-手机安装三件套.zip`

注意：文档里的 Markdown 表示会显示反斜杠；真正输入 Windows 文件选择器时，必须是普通 Windows 路径，不得变成文本意义上的双反斜杠。

## 1.2 Step A — 观察当前 GUI，而不是先造 workaround

先看当前微信聊天界面。

如果输入框工具栏已经有明确“文件/文件夹”图标：

> **直接走原生添加文件路径。**

禁止在原生入口还没验证失败前先做：

- 自制拖拽窗口；
- OCR 扫描；
- 搜索微信协议；
- 搜索“文件传输助手”网页入口；
- PowerShell 模拟发送；
- 额外打开多个 Explorer；
- 关闭用户其它窗口。

本次真实失败中，最大的低效来源之一就是：

> 明明微信输入框下方已经有文件夹按钮，却过早绕到搜索、拖拽助手、OCR、剪贴板和窗口重排。

## 1.3 Step B — 确认目标窗口与坐标归属

点击前确认：

1. 当前微信窗口边界；
2. 当前前台窗口；
3. 鼠标目标点实际属于哪个顶层窗口。

必要时使用：

- `GetForegroundWindow`
- `WindowFromPoint`
- 顶层窗口枚举
- UIA BoundingRectangle
- Windows-MCP Snapshot / Screenshot

目标是避免这种情况：

> “视觉上微信在这里，但实际坐标被另一窗口/overlay/文件资源管理器挡住。”

如果命中测试表明目标点确实属于微信，就不要继续怀疑“被别的窗口挡住”。

## 1.4 Step C — Qt 自绘控件：UIA 看不到，不代表按钮不存在

微信工具栏是 Qt 自绘 UI。

可能出现：

- UI Automation 无法给出“添加文件”这个语义元素；
- 但 Screenshot 中按钮清晰可见。

此时正确 fallback：

1. 获取**当前实时 Screenshot**；
2. 识别工具栏各图标；
3. 计算目标中心；
4. 将 Screenshot 坐标转换为 screen coordinates；
5. 只点击一次；
6. 立即验证后态。

禁止：

> “UIA 没找到元素 -> 这个按钮不存在”。

## 1.5 Step D — 点击以后，先检查有没有“新状态”，不要只检查某一种窗口类

本次实际发现了一个很关键的坑：

微信点“添加文件”以后，前台窗口可能是：

- 微信自己的 Qt `选择文件` 窗口；
- 标准 Windows `#32770` 文件选择器；
- 甚至 Qt wrapper 再进入标准 Windows selector。

因此：

> **不要把“文件选择器出现”硬编码成 class == #32770。**

正确观察方法：

- 枚举所有可见顶层窗口；
- 看标题、class、矩形、前台 handle；
- 特别检查：
  - `选择文件`
  - `打开`
  - Qt dialog
  - `#32770`

本次曾发生：

> Click 实际已经打开了 Qt “选择文件”，但检测逻辑只找 `#32770`，于是错误结论变成“Click 没生效”。

这是典型的：

> **Observer failure，不是 Action failure。**

## 1.6 Step E — 文件选择器可能是多层状态机

不要假设“点一次添加文件 -> 一个标准文件选择器 -> 完成”。

真实流程可能是：

`微信主窗口`
→ `Qt 选择文件 wrapper`
→ `标准 Windows #32770 selector`
→ `返回微信待发送状态`

每次点击“打开”后，都要重新观察：

- 当前前台窗口是谁；
- 标题/class 是否变化；
- 是否进入下一层 selector；
- 是否已经回到微信。

不能把第一层“打开”误认为整个文件选择流程已经结束。

## 1.7 Step F — 文件路径输入必须是“文件系统真实文本”

本次真实失败：

系统明确报：

> `C:\\Users\\... 文件名无效`

根因不是文件不存在，而是 Agent 把程序字符串转义形式当成了 GUI 要输入的真实文本。

规则：

- API/JSON/PowerShell 的字符串转义属于**传输层**；
- Windows 文件选择框需要的是**实际路径文本**；
- 最终 GUI 中应看到普通路径：
  `C:\Users\24734\Desktop\xxx.zip`
- 不得把 `\\` 的程序表示形式原样打进输入框。

在点“打开”前最好验证：

- 文件真实存在；
- 输入框里展示的路径是正常 Windows path；
- 没有多余引号、反斜杠、换行或乱码。

## 1.8 Step G — “打开”后必须确认已经回到微信

只有看到：

- 文件选择窗口消失；
- 前台重新回到微信主窗口；

才能认为：

> 文件选择阶段结束。

但这还**不是发送成功**。

下一步必须确认文件已经进入微信待发送状态。

## 1.9 Step H — UIA 读不到文件卡片时，用视觉后态，不要误判失败

微信 Qt 自绘输入区可能不把 ZIP 文件名暴露给 UIA。

所以：

`FOUND=0`

只意味着：

> UIA 没读到对应 accessible text。

它不能证明：

> 文件没有挂到输入区。

正确 fallback：

- 当前 Screenshot 与“空输入框基线”比较；
- 输入区发生明显结构变化；
- 文件卡片/占位块视觉出现；
- 发送按钮状态变化；
- 其它可观察语义变化。

本次真实案例使用了像素差作为辅助证据：

- 文件挂入后，输入区域与空基线发生明显变化；
- 这才支持“待发送文件已进入微信”的判断。

像素差只能作为 fallback evidence，不应替代可读的业务语义证据。

## 1.10 Step I — 发送以后再验证一次

按 Enter / 点击发送之后：

至少验证两件事：

1. 输入区从“待发送文件状态”恢复；
2. 聊天区出现新的内容变化/文件卡片。

如果 UIA 能读出文件名，则优先使用：

> 聊天记录实际出现目标 ZIP 文件名。

如果 Qt 自绘导致 UIA 不可见，则使用组合证据：

- 待发送输入区消失；
- 聊天区域新增卡片/布局变化；
- 发送动作后没有错误弹窗；
- 必要时截图视觉检查。

## 1.11 微信上传完成门

只有满足以下链路，才允许说“已经发送”：

`正确聊天`
→ `添加文件入口真实触发`
→ `目标文件被选择`
→ `返回微信`
→ `文件进入待发送状态`
→ `发送动作执行`
→ `待发送状态消失`
→ `聊天记录产生对应新内容`

任何中间状态都不能提前汇报为“已发送”。

---

# 2. 宏观经验：这次所有失败点到底说明了什么

## 2.1 原生 GUI 路径优先，workaround 必须后置

错误模式：

> 看见一个 GUI 问题，先想脚本、拖拽 helper、OCR、协议、CLI。

正确顺序：

1. 原生可访问控件；
2. 原生快捷键；
3. 当前实时视觉坐标；
4. 系统文件选择器；
5. 原生 drag/drop；
6. 只有原生路径验证不可用以后，才考虑 workaround。

原则：

> **不要把“能技术绕过”误认为“应该技术绕过”。**

---

## 2.2 DPI scale 与 Screenshot scale 是两层完全不同的问题

当前机器实测：

- Physical display: `2560 × 1600`
- Effective DPI: `168`
- Windows scale: `175%`
- Windows-MCP: Per-Monitor DPI Aware
- 某次 Screenshot 又返回：
  `Screenshot Coordinate Scale = 1.481481`

结论：

> Windows DPI awareness 正确，并不意味着返回给模型的 Screenshot 使用原始物理像素。

存在至少四套坐标：

1. Physical / virtual desktop coordinates
2. DPI logical coordinates
3. Windows-MCP returned screenshot coordinates
4. 用户上传/远程桌面截图坐标

不得混用。

---

## 2.3 用户上传截图只能做“视觉参考”，不能直接当 Click 坐标

用户从手机、远程桌面或聊天上传的截图：

- 可能被客户端缩放；
- 可能裁剪；
- 可能带黑边；
- 可能经过二次压缩；
- 可能已经不是当前窗口位置。

因此：

> 用户截图可以帮助理解“哪个图标是目标”，但不能直接把其像素坐标传给 Windows-MCP Click。

必须重新映射到当前实时 Windows Screenshot。

---

## 2.4 动作失败和观察失败必须分开

这是本次最重要的宏观经验之一。

### Action failure

例：

- Click 根本没落到目标控件；
- 输入没有进入目标文本框；
- Enter 被别的窗口接收。

### Observer failure

例：

- Click 已经打开“选择文件”，但检测逻辑只找 `#32770`；
- Qt 文件卡片已出现，但 UIA `FOUND=0`；
- 已经切换到下一层 dialog，但仍按旧窗口结构判断。

恢复路径完全不同。

因此失败后第一问不是：

> “要不要再点一次？”

而是：

> “动作没发生，还是动作发生了但我没观察到？”

---

## 2.5 不要硬编码一种窗口 class / 一种 dialog 实现

Windows GUI 自动化常见错误：

> “文件选择器一定是 #32770。”

真实世界可能是：

- Qt wrapper；
- Electron dialog；
- WinUI；
- standard common dialog；
- 自定义宿主窗口；
- 多层 wrapper。

规则：

> 标题、class、foreground handle、visible top-level windows、窗口几何必须组合判断。

不要把 class name 当业务状态的唯一真相。

---

## 2.6 前台窗口变化本身就是状态证据

本次发现：

`SetForegroundWindow(微信)`

之后真正的 foreground handle 可能变成：

`选择文件`

这不是失败，而是 GUI 状态机推进了。

因此应记录：

- before foreground
- after action foreground
- new title/class/rect

前台窗口变化可以直接帮助判断：

> 动作是否成功进入下一层。

---

## 2.7 Hit-test 是排查“为什么点不准”的高价值工具

当视觉坐标已经确认，但 Click 不生效时：

使用：

- `WindowFromPoint`
- root ancestor

确认：

> 这个坐标当前到底属于谁。

如果命中：

> 微信 Qt window

就能排除：

- 被 Explorer 遮挡；
- 被透明 overlay 截获；
- 点到别的应用。

不要反复移动窗口猜原因。

---

## 2.8 UIA 不可见不等于 UI 不存在

Qt/Electron/canvas/self-drawn UI 中，常见：

- 按钮视觉存在；
- UIA tree 没 label；
- 文件卡片视觉存在；
- UIA 没文本。

因此证据层级应是：

1. semantic/accessibility evidence
2. window-state evidence
3. screenshot visual evidence
4. pixel/layout delta fallback

不能反过来因为 UIA 空就宣布业务失败。

---

## 2.9 Click 返回成功不是业务成功

Windows-MCP 返回：

> `Single left clicked at (...)`

只证明：

> 输入事件注入成功。

不证明：

- 点中了正确按钮；
- 按钮接受了事件；
- 文件选择器打开了；
- ZIP 被加载了；
- 文件被发送了。

同理：

- `Pressed enter`
- `Typed text`

也都只是 primitive 成功。

业务成功必须验证业务后态。

---

## 2.10 GUI 执行必须“一步一观察”，不能连点一串

错误模式：

`Snapshot -> Click A -> Click B -> Enter -> report success`

只要 A 后界面变化，B 的坐标/焦点就可能已经失效。

正确：

`Observe -> A -> Verify`
`Observe -> B -> Verify`
`Observe -> Send -> Verify`

尤其适用于：

- 安装器；
- 文件选择器；
- 微信/QQ；
- 设置页；
- 权限弹窗；
- 多层 modal。

---

## 2.11 窗口管理默认保护用户状态

本次用户明确指出：

> 其它已经开的窗口不要随便叉掉，最多最小化。

这应该成为通用规则：

- target: bring-to-front / focus / restore
- obstruction: minimize / background / move / Snap
- pre-existing window: 默认不 Close
- Agent-created temporary window: 完成后可精确清理
- 不使用 `Alt+F4` 作为“腾位置”的默认办法

---

## 2.12 不要过早创建 helper window

本次曾创建：

> `JARVIS ZIP Drag Source`

这是典型过度工程。

只有满足以下条件才允许 helper UI：

- 原生添加文件入口已验证不可用；
- 原生系统 file chooser 不可用；
- clipboard file paste 不可用；
- drag/drop 是目标应用真正支持且更可靠的路径。

否则 helper window 只会增加：

- 更多焦点；
- 更多坐标；
- 更多窗口遮挡；
- 更多临时文件；
- 更多 cleanup 成本。

---

## 2.13 CLI 的正确角色：准备与诊断，不代替 GUI 业务动作

CLI/PowerShell 可用于：

- 确认 ZIP 存在；
- 核对 SHA；
- 查询窗口；
- 读取分辨率/DPI；
- 枚举 top-level window；
- 做 hit-test；
- 检查 foreground；
- 清理由 Agent 明确创建的临时文件。

但如果用户的目标是：

> “在微信 GUI 里上传文件”

业务动作本身仍应优先：

> Windows-MCP GUI。

CLI 不应偷换成：

> “我用脚本做了一个等价动作，所以算完成”。

---

## 2.14 路径转义、编码、剪贴板属于 Input correctness

GUI automation 失败并不总是定位问题。

本次明确遇到：

> 输入路径被转义成双反斜杠 -> Windows 报文件名无效。

所以失败分类里必须有：

> INPUT_ERROR / ENCODING_ERROR / ESCAPING_ERROR

不要看到文件选择器报错就继续怀疑鼠标坐标。

---

## 2.15 对“没有证据”的成功报告必须零容忍

本次最严重的执行错误不是点歪，而是：

> 在没有看到真正后态时提前说“已经发送”。

规则：

> 没有后态证据，就只能说“动作已执行，结果待验证”。

“完成”必须绑定可验证 evidence。

---

# 3. Windows-MCP 标准状态机

## 3.1 OBSERVE

收集当前真实状态：

- target window
- foreground window
- visible top-level windows
- target rect
- UIA tree
- current Screenshot
- Screenshot metadata
- display/DPI
- cursor position
- blocking dialog

## 3.2 CLASSIFY

先判断当前问题属于哪一类：

### ELEMENT_NOT_EXPOSED

UIA 看不到 Qt/Electron 自绘元素。

→ 转视觉定位。

### COORDINATE_SPACE_MISMATCH

截图坐标、物理 screen 坐标、用户截图坐标混用。

→ 重新读取 metadata + 转换。

### STALE_STATE

窗口移动/弹窗出现以后还在用旧坐标。

→ 重新 Snapshot。

### FOCUS_FAILURE

输入发给了错误窗口。

→ 获取 foreground，restore/focus target，再操作。

### ACTION_FAILURE

动作真的没有发生。

→ 重新定位、换 interaction primitive。

### OBSERVER_FAILURE

动作已经发生，但检测器没识别。

→ 放宽观察策略：全顶层窗口、标题/class、截图、pixel delta。

### DIALOG_LAYER_CHANGED

进入了另一层 Qt/native selector。

→ 重新 Observe，新窗口视为新状态。

### INPUT_ERROR

路径、编码、剪贴板、转义、文本错误。

→ 修输入，不继续调坐标。

### CAPABILITY_GAP

当前 Windows-MCP primitive 确实无法完成。

→ 才进入 Desktop Commander / helper / alternative route。

## 3.3 LOCATE

优先级：

1. accessibility semantic
2. keyboard navigation
3. current Screenshot visual target
4. screen coordinate

## 3.4 CONVERT

若视觉来自 Windows-MCP Screenshot：

`screen_x = region_left + round(image_x * screenshot_scale)`

`screen_y = region_top + round(image_y * screenshot_scale)`

不要额外套 Windows DPI 175%，除非当前数据明确是 DPI logical coordinates。

## 3.5 ACT

一次一个动作。

不连点，不扫坐标。

## 3.6 VERIFY

验证业务后态。

验证失败后先 Classify，而不是直接 Retry。

## 3.7 CONTINUE

只有前一步后态确认后，才能进入下一步。

## 3.8 LEARN

任务恢复后判断：

> 这是一次性事故，还是可复用 failure pattern？

若可复用：

- 更新 workflow；
- 增加 eval；
- validator PASS；
- 未来默认规避。

---

# 4. 实时视觉校准算法

每次需要视觉坐标点击时：

## OBSERVE

读取：

- `DisplayInventory`
- 当前实时 `Screenshot`
- `Screenshot Original Size`
- `Screenshot Coordinate Scale`
- `Screenshot Region`
- `Visible/Selected Displays`
- 当前目标窗口 rect

只使用当前截图。

窗口移动、最大化/恢复、DPI/显示器切换、modal 出现以后，旧坐标立即 stale。

## LOCATE

在当前返回图像中得到：

`image_x, image_y`

如果目标来自用户上传截图：

> 只拿它识别“哪个图标/哪个按钮”，不能直接使用其像素坐标。

## CONVERT

`screen_x = region_left + round(image_x * s)`

`screen_y = region_top + round(image_y * s)`

若 `s=1`，仍要考虑 region origin / multi-display offset。

## ACT

只点一次。

## VERIFY

确认：

> 业务状态改变了吗？

如果没有：

1. hit-test
2. foreground check
3. top-level window check
4. observer failure check
5. 再决定是否 retry

---

# 5. 窗口管理规则

GUI 自动化默认保护用户当前桌面状态：

- 目标应用：bring-to-front / focus / restore。
- 用户原本已经打开的其它窗口不得随便关闭。
- 腾位置：优先 minimize / background / move / Snap。
- 只有用户明确要求关闭，或窗口明确由当前 Agent 临时创建且关闭无风险时，才允许 Close。
- 不为了拖拽/上传先关掉用户已有窗口。
- 不因为窗口挡路就自动 `Alt+F4`。
- 临时 helper / screenshot / script 必须在完成后精确清理，不使用 broad clean。

---

# 6. 什么时候允许 fallback

只有在当前原生 GUI 路径已经有证据证明不可用时才 fallback。

推荐阶梯：

`Native control`
→ `Keyboard / accessibility`
→ `Visual click`
→ `Native file chooser`
→ `Clipboard file paste`
→ `Native drag/drop`
→ `Same-tool alternate primitive`
→ `Desktop Commander / helper`

禁止：

> 第一步不顺手就直接跳到最复杂方案。

---

# 7. GUI 成功证据等级

从强到弱：

1. 业务语义直接可读
   例：聊天记录出现目标文件名。
2. 应用状态明确改变
   例：前台从 chooser 回到微信，输入区出现文件卡片。
3. 可访问树 / window state 改变。
4. Screenshot 视觉结构改变。
5. Pixel delta。

最低要求：

> 不能只有 primitive result。

---

# 8. 汇报规则

## 可以说“已完成”

只有：

- 目标动作已执行；
- 关键后态已验证；
- 没有尚未处理的错误弹窗；
- 没有把“准备完成”误报成“业务完成”。

## 只能说“动作已执行，结果待验证”

例如只有：

- `Click success`
- `Enter pressed`
- `Type success`

但没有业务后态。

## 不能说“失败”

如果：

- UIA 看不到；
- 固定 class detector 没匹配；
- Snapshot 返回空；

在确认动作本身失败前，应先考虑：

> Observer failure。

---

# 9. Windows-MCP 工具级未来改进候选

当前先不修改源码。

但这次实战支持未来评估以下能力：

- `coordinate_space = screen | screenshot`
- `capture_id + image_loc`
- Screenshot scale / region / display offset 自动转换
- Click 后自动返回 foreground/window delta
- built-in hit-test
- built-in post-action screenshot
- dialog discovery 不依赖单一 class
- expose active top-level modal
- screenshot coordinate mapping metadata machine-readable
- native `ClickScreenshot(capture_id, x, y)`

核心目标：

> 把模型必须手算、手猜的坐标合同下沉到工具层。

---

# 10. Windows-MCP GUI Checklist

执行桌面 GUI 前快速检查：

### Before action

- [ ] 当前目标窗口是谁？
- [ ] foreground 是谁？
- [ ] 有没有 modal？
- [ ] UIA 能否直接定位？
- [ ] Screenshot 是当前的吗？
- [ ] Screenshot scale / region 是否已读？
- [ ] 坐标属于当前 Screenshot 还是用户上传图片？
- [ ] 目标点 hit-test 属于谁？
- [ ] 用户其它窗口是否被保护？

### After action

- [ ] 业务后态是什么？
- [ ] foreground 是否变化？
- [ ] 是否出现新 dialog layer？
- [ ] 检测失败是 Action failure 还是 Observer failure？
- [ ] 是否需要重新 Screenshot？
- [ ] 是否错误复用了旧坐标？

### Before reporting success

- [ ] 真正业务结果是否可见？
- [ ] 是否仍有 pending dialog / error？
- [ ] 是否只是 primitive success？
- [ ] 是否清理了当前 Agent 自己创建的临时资源？
- [ ] 是否没有关闭用户原有窗口？

---

# 11. 最终原则

Windows-MCP 使用质量取决于三件事：

1. **正确理解当前 GUI 状态**
2. **选择最简单的原生交互路径**
3. **每一步都验证真实后态**

真正稳定的桌面 Agent 不是：

> “鼠标点得快。”

而是：

> **知道自己看到了什么、点击了什么、点击后发生了什么；如果与预期不一致，先判断是动作失败还是观察失败，再恢复。**
