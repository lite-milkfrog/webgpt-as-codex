import fs from 'node:fs';
import crypto from 'node:crypto';
import { McpHttpSession, parseResultJson } from './mcp-http-client.mjs';

function argValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

const promptPath = argValue('--prompt');
const resumeFilled = process.argv.includes('--resume-filled');
const endpoint =
  argValue('--endpoint') ||
  process.env.PLAYWRIGHT_MCP_ENDPOINT ||
  'http://localhost:8931/mcp';

if (!promptPath) {
  console.error('Usage: node chatgpt-loop-handoff.mjs --prompt <path> [--endpoint <mcp-url>]');
  process.exit(2);
}

const prompt = fs.readFileSync(promptPath, 'utf8');
if (!prompt.trim()) throw new Error(`Prompt is empty: ${promptPath}`);

const normalize = (text) => text.replace(/\s+/g, '');
const sha256 = (text) => crypto.createHash('sha256').update(text, 'utf8').digest('hex');
const expectedHash = sha256(normalize(prompt));

const mcp = new McpHttpSession(endpoint);
await mcp.initialize({ clientName: 'computer-agent-chatgpt-loop-handoff' });

const tools = await mcp.listTools();
const toolNames = new Set((tools?.result?.tools ?? []).map((tool) => tool.name));
const required = ['browser_tabs', 'browser_evaluate', 'browser_type', 'browser_wait_for'];
for (const name of required) {
  if (!toolNames.has(name)) throw new Error(`Playwright MCP missing required tool: ${name}`);
}
if (!toolNames.has('browser_press_key') && !toolNames.has('browser_evaluate')) {
  throw new Error('No supported submit primitive is available');
}

async function call(name, args = {}) {
  return (await mcp.callTool(name, args)).text;
}

async function pageState() {
  const text = await call('browser_evaluate', {
    function: `async () => {
      const composer = document.querySelector('#prompt-textarea');
      const composerText = composer?.innerText ?? '';
      const normalized = composerText.replace(/\\s+/g, '');
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(normalized));
      const composerHash = [...new Uint8Array(digest)]
        .map((b) => b.toString(16).padStart(2, '0')).join('');
      const users = [...document.querySelectorAll('[data-message-author-role="user"]')];
      const last = users.at(-1);
      const lastText = last?.innerText ?? last?.textContent ?? '';
      const send = document.querySelector('button[data-testid="send-button"]');
      return {
        url: location.href,
        title: document.title,
        composerLength: composerText.length,
        composerHash,
        composerFocused: document.activeElement === composer,
        userMessages: users.length,
        lastUserStart: lastText.slice(0, 180),
        lastUserEnd: lastText.slice(-260),
        hasStop: !!document.querySelector('button[data-testid="stop-button"]'),
        assistantMessages: document.querySelectorAll('[data-message-author-role="assistant"]').length,
        hasSend: !!send,
        sendDisabled: !!send?.disabled || send?.getAttribute('aria-disabled') === 'true'
      };
    }`,
  });
  const parsed = parseResultJson(text);
  if (!parsed) throw new Error(`Cannot parse Playwright state:\n${text.slice(0, 2000)}`);
  return parsed;
}

function isSubmitted(state) {
  return (
    state.userMessages >= 1 &&
    state.composerLength === 0 &&
    state.url.includes('/c/')
  );
}

async function verifyTakeover(state) {
  if (!isSubmitted(state)) return false;
  if (state.hasStop || state.assistantMessages > 0) return true;
  await call('browser_wait_for', { time: 2 });
  const later = await pageState();
  return later.hasStop || later.assistantMessages > 0;
}

async function focusComposer() {
  const text = await call('browser_evaluate', {
    function: `() => {
      const composer = document.querySelector('#prompt-textarea');
      if (!composer) return { focused: false, reason: 'composer-missing' };
      composer.focus();
      return { focused: document.activeElement === composer };
    }`,
  });
  const parsed = parseResultJson(text);
  if (!parsed?.focused) throw new Error(`Cannot focus ChatGPT composer: ${text.slice(0, 1000)}`);
}

async function activateSendButton() {
  const text = await call('browser_evaluate', {
    function: `() => {
      const element = document.querySelector('button[data-testid="send-button"]');
      if (!element || element.disabled || element.getAttribute('aria-disabled') === 'true') {
        return { clicked: false, reason: 'disabled-or-missing' };
      }
      element.click();
      return { clicked: true };
    }`,
  });
  return parseResultJson(text);
}

let state;
if (resumeFilled) {
  // Recovery mode deliberately performs no fill. It is safe only when the currently
  // selected ChatGPT tab already contains the exact prompt hash from an earlier run.
  await call('browser_wait_for', { time: 0.5 });
  state = await pageState();
  if (isSubmitted(state)) {
    if (!(await verifyTakeover(state))) throw new Error('Existing submission found, but takeover/generation was not observed');
    console.log('HANDOFF_OK');
    console.log(`conversation=${state.url}`);
    console.log(`prompt_chars=${prompt.length}`);
    console.log(`prompt_normalized_sha256=${expectedHash}`);
    process.exit(0);
  }
  if (state.userMessages !== 0 || state.composerHash !== expectedHash || !state.hasSend || state.sendDisabled) {
    throw new Error(`Resume-filled state is not the exact unsent prompt; refusing refill/submit: ${JSON.stringify(state)}`);
  }
} else {
  // Normal mode always creates a fresh ChatGPT tab. Tab indexes are session-scoped,
  // so every tabs/list/select/new sequence must happen inside this same MCP session.
  await call('browser_tabs', { action: 'new', url: 'https://chatgpt.com/' });
  await call('browser_wait_for', { time: 1 });

  state = await pageState();
  if (state.userMessages !== 0 || state.composerLength !== 0) {
    throw new Error(`New ChatGPT target is not blank: ${JSON.stringify(state)}`);
  }

  let fillError = null;
  try {
    await call('browser_type', {
      target: '#prompt-textarea',
      element: 'ChatGPT message composer',
      text: prompt,
      submit: false,
      slowly: false,
    });
  } catch (error) {
    // Long ProseMirror fills can exceed the MCP call timeout even when the text was fully inserted.
    // Do not retry until post-state proves the fill did not happen.
    fillError = error;
  }

  state = await pageState();
  if (state.userMessages !== 0) {
    throw new Error('Unexpected user message appeared during fill; refusing any submit retry');
  }
  if (state.composerHash !== expectedHash) {
    const detail = fillError ? ` Initial fill error: ${fillError.message}` : '';
    throw new Error(`Composer hash mismatch; refusing submit.${detail}`);
  }
  if (!state.hasSend || state.sendDisabled) {
    throw new Error(`Send button is not enabled: ${JSON.stringify(state)}`);
  }
}

// Prefer normal keyboard semantics first. If Enter does not submit, verify post-state before
// using a same-semantic DOM activation of the already-enabled send button.
if (!state.composerFocused) {
  // Some Playwright MCP versions interpret browser_evaluate.target as a snapshot/ref
  // selector rather than raw CSS. Query the DOM inside the already-authorized page
  // evaluation instead of passing '#prompt-textarea' through that target channel.
  await focusComposer();
  state = await pageState();
}

let enterError = null;
if (toolNames.has('browser_press_key')) {
  try {
    await call('browser_press_key', { key: 'Enter' });
  } catch (error) {
    enterError = error;
  }
  await call('browser_wait_for', { time: 1 });
  state = await pageState();
}

if (!isSubmitted(state)) {
  if (state.userMessages !== 0 || state.composerHash !== expectedHash) {
    throw new Error('Enter produced an ambiguous post-state; refusing a second submit action');
  }

  const activationResult = await activateSendButton();
  if (!activationResult?.clicked) {
    const detail = enterError ? ` Enter error: ${enterError.message}` : '';
    throw new Error(`DOM submit activation failed.${detail}`);
  }
  await call('browser_wait_for', { time: 1 });
  state = await pageState();
}

if (!isSubmitted(state)) {
  throw new Error(`Submission post-state not confirmed; do not retry automatically: ${JSON.stringify(state)}`);
}
if (!state.lastUserStart.includes('JARVIS') && !state.lastUserStart.includes('Loop Engineering')) {
  throw new Error('Submitted message identity is not recognizable as the intended handoff prompt');
}
if (!(await verifyTakeover(state))) {
  throw new Error('Prompt was submitted, but next conversation takeover/generation was not observed');
}

console.log('HANDOFF_OK');
console.log(`conversation=${state.url}`);
console.log(`prompt_chars=${prompt.length}`);
console.log(`prompt_normalized_sha256=${expectedHash}`);
