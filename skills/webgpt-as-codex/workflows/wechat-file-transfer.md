# WeChat File Transfer Assistant — Canonical Windows-MCP Workflow

> Canonical workflow for sending a local file through the already logged-in WeChat PC client to **文件传输助手**.
>
> This file supersedes ad-hoc coordinate guessing for this task. General Qt/high-DPI lessons remain in `windows-gui-visual-calibration.md`.

## 0. Completion contract

A file-send task is complete only when the business post-state is verified:

`target file exists`
→ `already logged-in WeChat session is taken over`
→ `文件传输助手 is the active chat`
→ `file enters pending-send state`
→ `send is executed`
→ `pending state clears`
→ `the chat contains a new corresponding file card/content`.

`Click success`, `Ctrl+V success`, `Pressed enter`, or a tool returning success are **not** completion evidence by themselves.

## 1. Never restart an already logged-in WeChat

If WeChat is already running and logged in:

1. enumerate/identify the existing WeChat top-level window or taskbar instance;
2. restore / bring-to-front that existing window;
3. observe the live state;
4. continue from that state.

Do **not** launch WeChat again from Start/menu/shortcut merely to obtain focus. A second launch may surface a login page, update prompt, helper wrapper, or secondary Qt window and create a false conclusion that the user is logged out.

If both a login/helper window and a logged-in main window exist, preserve the logged-in main window and treat the extra window as a wrong branch unless evidence proves otherwise.

## 2. If the user already positioned the target chat, trust that state

If the user explicitly says or shows that **文件传输助手 is already open**, do not search for it again.

Treat this as authoritative task state unless the current live screenshot contradicts it.

The next step should be the file-send action, not re-navigation.

## 3. WeChat business verification is Screenshot-only

WeChat desktop UI is heavily Qt/self-drawn and does not reliably expose a complete UI Tree.

For **business-state verification**, only accept visual screenshot evidence:

1. current Windows-MCP original/highest-resolution Screenshot;
2. user-provided clear original screenshot for semantic state confirmation;
3. current screenshot-to-screenshot visual delta when needed.

UI Tree/UIA is **not acceptance evidence** for WeChat business state. It may be used only for non-business metadata such as:

- top-level window enumeration;
- window title/class;
- foreground/focus state.

It must not be used to conclude that a button, attachment, message, or sent file does not exist.

UI Tree may omit:
- the paperclip/folder file button;
- pending file cards;
- sent file card text.

Therefore `UIA_FOUND=0` is ignored as a business-state verdict.

If UI Tree and Screenshot disagree, **Screenshot wins**.

### User-provided screenshot rule

A user-uploaded screenshot is valid **semantic state evidence**: it can prove that the user is logged in, which chat is open, and what controls are visible.

But its pixel coordinates are not automatically Windows-MCP click coordinates. For actual mouse actions, obtain a fresh Windows-MCP Screenshot and use its current coordinate metadata / live window geometry.

## 4. Preferred send path when 文件传输助手 is already open

For an already-open chat, the most reliable tested path is:

### A. Verify the local file

Confirm exact path, size/version if relevant, and that it is the intended artifact.

### B. Put the file onto the Windows file clipboard

Use a structured host/file operation to set a **FileDropList** containing the exact file.

This is preparation only; it is not the business send action.

### C. Focus the existing WeChat input area

Bring the existing logged-in WeChat window to front and focus the current 文件传输助手 composer/input region.

Do not restart WeChat.

### D. Paste with Windows-MCP

Use Windows-MCP keyboard action:

`Ctrl+V`

This is the preferred fallback when the Qt file-button / chooser path is unreliable or not exposed to UIA.

### E. Verify pending-send state

Re-observe the current live screenshot.

Accept evidence such as:
- a file card/attachment block appearing in the composer;
- input area structure changing from the empty baseline;
- send control becoming active;
- directly visible target filename, if exposed.

Do not use UIA text as the verifier for Qt file cards. Verify visually from the Screenshot.

### F. Send

Use the application's normal send action, typically `Enter` if that is the current chat behavior.

### G. Verify business post-state

Confirm:
- pending attachment state is gone;
- chat history contains a new file card/content;
- no error dialog appeared.

If the user visibly confirms the file appeared in 文件传输助手, that is strong business-state evidence.

Only then report “sent”.

## 5. Native file-button / chooser path is secondary, not mandatory

If the file button is clearly accessible and semantically reliable, the native path remains valid:

`file button → chooser → exact path → open → pending card → send → verify`.

But for WeChat Qt:

- one failed/ambiguous self-drawn button click must not trigger repeated coordinate guessing;
- do not keep moving the window and testing arbitrary locations;
- after one observed native-control failure/ambiguity, prefer the tested FileDropList + `Ctrl+V` path.

This is not “bypassing the GUI”: the file is still pasted and sent through the active WeChat chat UI. The host step only prepares the OS file clipboard.

## 6. Coordinate-space rule

Never mix:
- user screenshot pixels;
- Windows-MCP Screenshot pixels;
- Windows physical screen coordinates;
- Windows DPI scale.

If an actual click is necessary:

1. take a fresh Windows-MCP Screenshot;
2. read its actual image size / coordinate scale / region;
3. identify the target in that current image;
4. convert once;
5. hit-test/act once;
6. verify post-state.

Do not derive click coordinates from an older user screenshot even when its visual content is clear.

## 7. Failure taxonomy

When the expected state is not visible, classify first:

- `WRONG_INSTANCE`: launched/reached login/helper window instead of existing logged-in main window;
- `OBSERVER_FAILURE`: UI changed but UIA/tree did not expose it; for WeChat this is expected enough that business verification must stay Screenshot-only;
- `COORDINATE_SPACE_MISMATCH`: screenshot and screen coordinates were mixed;
- `FOCUS_FAILURE`: paste/send went to the wrong window/control;
- `NATIVE_CONTROL_AMBIGUOUS`: Qt button click produced no verifiable state;
- `INPUT_ERROR`: wrong file/path/clipboard payload;
- `BUSINESS_POSTSTATE_MISSING`: primitive succeeded but file did not appear in chat.

Recovery order:

`re-observe live business state → preserve existing login session → same-window adaptation → FileDropList + Ctrl+V → send → business verification`.

## 8. 2026-09-19 validated incident

Validated artifact:
`C:\Users\24734\Desktop\JARVIS-2.11.3.zip`

Validated situation:
- WeChat was already logged in;
- 文件传输助手 was already open;
- restarting/reopening WeChat was unnecessary and caused confusion;
- UI Tree was insufficient for the Qt file controls/cards;
- the reliable path was Windows FileDropList → focus existing 文件传输助手 → Windows-MCP `Ctrl+V` → `Enter`;
- the user confirmed the file appeared successfully.

Reusable conclusion:

> **When the user already placed WeChat on 文件传输助手, stop navigating and send the file through that live chat. Prefer the existing logged-in instance and the tested file-clipboard paste path over repeated Qt coordinate guessing.**
