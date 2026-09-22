import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { McpHttpSession, parseResultJson } from './mcp-http-client.mjs';

function argValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

const normalize = (text) => text.replace(/\s+/g, '');
const sha256 = (text) => crypto.createHash('sha256').update(text, 'utf8').digest('hex');

function classifyPromptState(state, expectedHash) {
  if (
    state.lastUserHash === expectedHash &&
    state.composerLength === 0 &&
    state.url.includes('/c/')
  ) {
    return 'submitted';
  }
  if (
    state.userMessages === 0 &&
    state.composerHash === expectedHash &&
    state.composerLength > 0
  ) {
    return 'draft';
  }
  return 'unrelated';
}

function runSelfTest() {
  const expectedHash = sha256(normalize('Loop Engineering handoff'));
  const emptyHash = sha256('');
  const unrelated = {
    url: 'https://chatgpt.com/c/unrelated',
    composerLength: 0,
    composerHash: emptyHash,
    userMessages: 1,
    lastUserHash: sha256(normalize('different message')),
  };
  const draft = {
    url: 'https://chatgpt.com/',
    composerLength: 24,
    composerHash: expectedHash,
    userMessages: 0,
    lastUserHash: emptyHash,
  };
  const submitted = {
    url: 'https://chatgpt.com/c/exact',
    composerLength: 0,
    composerHash: emptyHash,
    userMessages: 1,
    lastUserHash: expectedHash,
  };
  if (classifyPromptState(unrelated, expectedHash) !== 'unrelated') {
    throw new Error('self-test failed: unrelated conversation misclassified');
  }
  if (classifyPromptState(draft, expectedHash) !== 'draft') {
    throw new Error('self-test failed: exact draft not recognized');
  }
  if (classifyPromptState(submitted, expectedHash) !== 'submitted') {
    throw new Error('self-test failed: exact submitted prompt not recognized');
  }
  const tabs = parseTabs(
    '### Tabs\n- 0: (current) [ChatGPT](https://chatgpt.com/c/exact)\n- 1: [Welcome](chrome-extension://example/welcome.html)'
  );
  if (
    tabs.length !== 2 ||
    tabs[0].index !== 0 ||
    !tabs[0].current ||
    tabs[0].url !== 'https://chatgpt.com/c/exact'
  ) {
    throw new Error('self-test failed: browser_tabs output parser drifted');
  }

  console.log('HANDOFF_SELF_TEST_OK');
}

if (process.argv.includes('--self-test')) {
  runSelfTest();
  process.exit(0);
}

const promptPath = argValue('--prompt');
const resumeFilled = process.argv.includes('--resume-filled');
const endpoint =
  argValue('--endpoint') ||
  process.env.PLAYWRIGHT_MCP_ENDPOINT ||
  'http://localhost:8931/mcp';

if (!promptPath) {
  console.error(
    'Usage: node chatgpt-loop-handoff.mjs --prompt <path> [--endpoint <mcp-url>] [--receipt-dir <path>] [--resume-filled] | --self-test'
  );
  process.exit(2);
}

const prompt = fs.readFileSync(promptPath, 'utf8');
if (!prompt.trim()) throw new Error(`Prompt is empty: ${promptPath}`);

const expectedHash = sha256(normalize(prompt));
const leaseToken = crypto.randomUUID();
const defaultReceiptRoot = process.env.LOCALAPPDATA
  ? path.join(process.env.LOCALAPPDATA, 'WebGPT-as-Codex', 'handoff-receipts')
  : path.join(os.homedir(), '.webgpt-as-codex', 'handoff-receipts');
const receiptDir =
  argValue('--receipt-dir') ||
  process.env.WEBGPT_HANDOFF_RECEIPT_DIR ||
  defaultReceiptRoot;
const receiptPath = path.join(receiptDir, `${expectedHash}.json`);

function readReceipt() {
  try {
    const value = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    return value?.promptHash === expectedHash ? value : null;
  } catch {
    return null;
  }
}

function writeReceipt(status, state, extra = {}) {
  fs.mkdirSync(receiptDir, { recursive: true });
  const payload = {
    schema: 1,
    status,
    promptHash: expectedHash,
    promptPath: path.resolve(promptPath),
    conversationUrl: state?.url ?? null,
    lastUserHash: state?.lastUserHash ?? null,
    composerHash: state?.composerHash ?? null,
    composerLength: state?.composerLength ?? null,
    updatedAt: new Date().toISOString(),
    ...extra,
  };
  const tempPath = `${receiptPath}.${process.pid}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  fs.renameSync(tempPath, receiptPath);
}

const mcp = new McpHttpSession(endpoint);
await mcp.initialize({ clientName: 'webgpt-as-codex-chatgpt-loop-handoff' });

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

function parseTabs(text) {
  const rows = [];
  const seen = new Set();
  for (const line of text.split(/\r?\n/)) {
    const match = line
      .trim()
      .match(/^- (\d+): (?:(\(current\)) )?\[[^\]]*\]\(([^)]+)\)/);
    if (!match) continue;
    const row = {
      index: Number(match[1]),
      current: Boolean(match[2]),
      url: match[3],
    };
    const key = `${row.index}|${row.current}|${row.url}`;
    if (!seen.has(key)) {
      seen.add(key);
      rows.push(row);
    }
  }
  return rows;
}

async function pageState() {
  const text = await call('browser_evaluate', {
    function: `async () => {
      const composer = document.querySelector('#prompt-textarea');
      const composerText = composer?.innerText ?? '';
      const normalized = composerText.replace(/\\s+/g, '');
      const composerDigest = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(normalized)
      );
      const composerHash = [...new Uint8Array(composerDigest)]
        .map((b) => b.toString(16).padStart(2, '0')).join('');

      const users = [...document.querySelectorAll('[data-message-author-role="user"]')];
      const last = users.at(-1);
      const lastText = last?.innerText ?? last?.textContent ?? '';
      const lastNormalized = lastText.replace(/\\s+/g, '');
      const lastDigest = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(lastNormalized)
      );
      const lastUserHash = [...new Uint8Array(lastDigest)]
        .map((b) => b.toString(16).padStart(2, '0')).join('');

      const send = document.querySelector('button[data-testid="send-button"]');
      let lease = null;
      try {
        lease = sessionStorage.getItem('__webgpt_as_codex_handoff_tab_lease_v1');
      } catch {}

      return {
        url: location.href,
        title: document.title,
        composerLength: composerText.length,
        composerHash,
        composerFocused: document.activeElement === composer,
        userMessages: users.length,
        lastUserHash,
        lastUserStart: lastText.slice(0, 180),
        lastUserEnd: lastText.slice(-260),
        hasStop: !!document.querySelector('button[data-testid="stop-button"]'),
        assistantMessages: document.querySelectorAll(
          '[data-message-author-role="assistant"]'
        ).length,
        hasSend: !!send,
        sendDisabled:
          !!send?.disabled || send?.getAttribute('aria-disabled') === 'true',
        lease
      };
    }`,
  });
  const parsed = parseResultJson(text);
  if (!parsed) {
    throw new Error(`Cannot parse Playwright state:\\n${text.slice(0, 2000)}`);
  }
  return parsed;
}

function isSubmittedMatch(state) {
  return classifyPromptState(state, expectedHash) === 'submitted';
}

async function pinCurrentTab() {
  const text = await call('browser_evaluate', {
    function: `() => {
      const token = ${JSON.stringify(leaseToken)};
      const key = '__webgpt_as_codex_handoff_tab_lease_v1';
      if (!location.href.startsWith('https://chatgpt.com/')) {
        return { pinned: false, url: location.href, lease: null };
      }
      sessionStorage.setItem(key, token);
      return {
        pinned: sessionStorage.getItem(key) === token,
        url: location.href,
        lease: sessionStorage.getItem(key)
      };
    }`,
  });
  const parsed = parseResultJson(text);
  if (!parsed?.pinned || parsed.lease !== leaseToken) {
    throw new Error(`Cannot pin ChatGPT target tab: ${text.slice(0, 1000)}`);
  }
}

async function ensurePinnedTab() {
  let state = await pageState();
  if (
    state.lease === leaseToken &&
    state.url.startsWith('https://chatgpt.com/')
  ) {
    return state;
  }

  const tabs = parseTabs(await call('browser_tabs', { action: 'list' }))
    .filter((row) => row.url.startsWith('https://chatgpt.com/'));
  for (const tab of tabs) {
    await call('browser_tabs', { action: 'select', index: tab.index });
    state = await pageState();
    if (
      state.lease === leaseToken &&
      state.url.startsWith('https://chatgpt.com/')
    ) {
      return state;
    }
  }
  throw new Error('Pinned ChatGPT handoff tab was lost; refusing to guess a target');
}

async function inspectExistingTarget() {
  const tabs = parseTabs(await call('browser_tabs', { action: 'list' }))
    .filter((row) => row.url.startsWith('https://chatgpt.com/'));
  let draft = null;
  let submitted = null;

  for (const tab of tabs) {
    await call('browser_tabs', { action: 'select', index: tab.index });
    await call('browser_wait_for', { time: 0.2 });
    const state = await pageState();
    const kind = classifyPromptState(state, expectedHash);
    if (kind === 'submitted') {
      if (submitted) {
        throw new Error(
          'Multiple exact submitted handoff targets found; refusing ambiguous recovery'
        );
      }
      submitted = { tab, state };
    } else if (kind === 'draft') {
      if (draft) {
        throw new Error(
          'Multiple exact unsent handoff drafts found; refusing ambiguous recovery'
        );
      }
      draft = { tab, state };
    }
  }

  if (submitted) return { kind: 'submitted', ...submitted };
  if (draft) return { kind: 'draft', ...draft };
  return null;
}

async function verifyTakeover(state) {
  if (!isSubmittedMatch(state)) return false;
  if (state.hasStop || state.assistantMessages > 0) return true;
  await call('browser_wait_for', { time: 2 });
  const later = await ensurePinnedTab();
  return (
    isSubmittedMatch(later) &&
    (later.hasStop || later.assistantMessages > 0)
  );
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
  if (!parsed?.focused) {
    throw new Error(`Cannot focus ChatGPT composer: ${text.slice(0, 1000)}`);
  }
}

async function activateSendButton() {
  const text = await call('browser_evaluate', {
    function: `() => {
      const element = document.querySelector('button[data-testid="send-button"]');
      if (
        !element ||
        element.disabled ||
        element.getAttribute('aria-disabled') === 'true'
      ) {
        return { clicked: false, reason: 'disabled-or-missing' };
      }
      element.click();
      return { clicked: true };
    }`,
  });
  return parseResultJson(text);
}

async function printSuccess(state, recovered = false) {
  writeReceipt('HANDOFF_OK', state, { recovered });
  console.log('HANDOFF_OK');
  console.log(`conversation=${state.url}`);
  console.log(`prompt_chars=${prompt.length}`);
  console.log(`prompt_normalized_sha256=${expectedHash}`);
  console.log(`receipt=${receiptPath}`);
  if (recovered) console.log('recovered_existing_handoff=true');
}

const priorReceipt = readReceipt();
if (priorReceipt?.status === 'HANDOFF_OK' && priorReceipt.conversationUrl) {
  console.log('HANDOFF_OK');
  console.log(`conversation=${priorReceipt.conversationUrl}`);
  console.log(`prompt_chars=${prompt.length}`);
  console.log(`prompt_normalized_sha256=${expectedHash}`);
  console.log(`receipt=${receiptPath}`);
  console.log('receipt_reused=true');
  process.exit(0);
}

if (priorReceipt?.status === 'SUBMITTED' && priorReceipt.conversationUrl) {
  await call('browser_tabs', {
    action: 'new',
    url: priorReceipt.conversationUrl,
  });
  await call('browser_wait_for', { time: 1 });
  let recovered = await pageState();
  if (!isSubmittedMatch(recovered)) {
    throw new Error(
      `A prior SUBMITTED receipt exists for this prompt, but the recorded conversation cannot be re-verified. Refusing duplicate submit: ${receiptPath}`
    );
  }
  await pinCurrentTab();
  recovered = await ensurePinnedTab();
  if (!(await verifyTakeover(recovered))) {
    throw new Error(
      `Exact prompt was already submitted previously, but takeover is not yet observable. Refusing duplicate submit: ${recovered.url}`
    );
  }
  await printSuccess(recovered, true);
  process.exit(0);
}

if (priorReceipt?.status === 'SUBMIT_ATTEMPTED') {
  const attemptedExisting = await inspectExistingTarget();
  if (attemptedExisting?.kind === 'submitted') {
    await pinCurrentTab();
    let recovered = await ensurePinnedTab();
    writeReceipt('SUBMITTED', recovered, { recoveredFromAttempt: true });
    if (!(await verifyTakeover(recovered))) {
      throw new Error(
        `A SUBMIT_ATTEMPTED receipt resolved to an exact submitted prompt, but takeover is not yet observable. Refusing duplicate submit: ${receiptPath}`
      );
    }
    recovered = await ensurePinnedTab();
    await printSuccess(recovered, true);
    process.exit(0);
  }
  const detail = attemptedExisting?.kind === 'draft'
    ? 'The exact prompt draft is still visible, but the previous submit attempt crossed the side-effect boundary.'
    : 'No exact prompt page is currently observable.';
  throw new Error(
    `A SUBMIT_ATTEMPTED receipt exists. ${detail} Refusing automatic resubmit; recover/verify the prior attempt without creating a second send: ${receiptPath}`
  );
}

let state;
const existing = await inspectExistingTarget();

if (existing?.kind === 'submitted') {
  await pinCurrentTab();
  state = await ensurePinnedTab();
  writeReceipt('SUBMITTED', state, { recovered: true });
  if (!(await verifyTakeover(state))) {
    throw new Error(
      `Exact prompt is already submitted at ${state.url}; refusing duplicate submit while takeover is unconfirmed`
    );
  }
  await printSuccess(state, true);
  process.exit(0);
}

if (existing?.kind === 'draft') {
  await pinCurrentTab();
  state = await ensurePinnedTab();
} else if (resumeFilled) {
  throw new Error(
    '--resume-filled requested, but no exact unsent prompt draft exists in the current Playwright context'
  );
} else {
  await call('browser_tabs', { action: 'new', url: 'https://chatgpt.com/' });
  await call('browser_wait_for', { time: 1 });

  state = await pageState();
  if (state.userMessages !== 0 || state.composerLength !== 0) {
    throw new Error(`New ChatGPT target is not blank: ${JSON.stringify(state)}`);
  }
  await pinCurrentTab();

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
    fillError = error;
  }

  state = await ensurePinnedTab();
  if (state.userMessages !== 0) {
    throw new Error(
      'Unexpected user message appeared during fill; refusing any submit retry'
    );
  }
  if (state.composerHash !== expectedHash) {
    const detail = fillError ? ` Initial fill error: ${fillError.message}` : '';
    throw new Error(`Composer hash mismatch; refusing submit.${detail}`);
  }
  if (!state.hasSend || state.sendDisabled) {
    throw new Error(`Send button is not enabled: ${JSON.stringify(state)}`);
  }
}

state = await ensurePinnedTab();
if (state.composerHash !== expectedHash || state.userMessages !== 0) {
  throw new Error(
    `Target is not the exact unsent handoff draft; refusing submit: ${JSON.stringify(state)}`
  );
}

if (!state.composerFocused) {
  await focusComposer();
  state = await ensurePinnedTab();
}

writeReceipt('SUBMIT_ATTEMPTED', state, {
  recoveredDraft: existing?.kind === 'draft',
});

let enterError = null;
if (toolNames.has('browser_press_key')) {
  try {
    await call('browser_press_key', { key: 'Enter' });
  } catch (error) {
    enterError = error;
  }
  await call('browser_wait_for', { time: 1 });
  state = await ensurePinnedTab();
}

if (!isSubmittedMatch(state)) {
  if (state.userMessages !== 0 || state.composerHash !== expectedHash) {
    throw new Error(
      'Enter produced an ambiguous post-state; refusing a second submit action'
    );
  }

  const activationResult = await activateSendButton();
  if (!activationResult?.clicked) {
    const detail = enterError ? ` Enter error: ${enterError.message}` : '';
    throw new Error(`DOM submit activation failed.${detail}`);
  }
  await call('browser_wait_for', { time: 1 });
  state = await ensurePinnedTab();
}

if (!isSubmittedMatch(state)) {
  throw new Error(
    `Exact submission post-state not confirmed; do not retry automatically: ${JSON.stringify(state)}`
  );
}

writeReceipt('SUBMITTED', state);
if (!(await verifyTakeover(state))) {
  throw new Error(
    `Exact prompt was submitted, but next conversation takeover/generation was not observed. Receipt written; do not submit again: ${receiptPath}`
  );
}

await printSuccess(state);
