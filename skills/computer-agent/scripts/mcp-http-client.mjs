export class McpHttpSession {
  constructor(endpoint) {
    this.endpoint = endpoint;
    this.sessionId = null;
    this.nextId = 10;
  }

  static parsePayload(text) {
    if (!text || !text.trim()) return null;
    const lines = text.split(/\r?\n/);
    const data = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n');
    return JSON.parse(data || text.trim());
  }

  async post(body) {
    const headers = {
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    };
    if (this.sessionId) headers['mcp-session-id'] = this.sessionId;

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const sessionId = response.headers.get('mcp-session-id');
    if (sessionId) this.sessionId = sessionId;

    const text = await response.text();
    if (!response.ok) {
      throw new Error(`MCP HTTP ${response.status}: ${text}`);
    }

    // MCP notifications may legitimately return 202/204 with an empty body.
    return McpHttpSession.parsePayload(text);
  }

  async initialize({
    protocolVersion = '2025-06-18',
    clientName = 'computer-agent-local-client',
    clientVersion = '1.0.0',
  } = {}) {
    const initialized = await this.post({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion,
        capabilities: {},
        clientInfo: { name: clientName, version: clientVersion },
      },
    });

    await this.post({
      jsonrpc: '2.0',
      method: 'notifications/initialized',
      params: {},
    });

    return initialized;
  }

  async listTools() {
    return this.post({
      jsonrpc: '2.0',
      id: this.nextId++,
      method: 'tools/list',
      params: {},
    });
  }

  async callTool(name, args = {}) {
    const response = await this.post({
      jsonrpc: '2.0',
      id: this.nextId++,
      method: 'tools/call',
      params: { name, arguments: args },
    });

    const content = response?.result?.content ?? [];
    const text = content
      .filter((item) => item.type === 'text')
      .map((item) => item.text ?? '')
      .join('\n');

    if (response?.result?.isError) {
      const error = new Error(`${name} failed: ${text}`);
      error.toolName = name;
      error.toolText = text;
      throw error;
    }

    return { response, text };
  }
}

export function parseResultJson(text) {
  const match = text.match(/### Result\s*\n([\s\S]*?)(?=\n### |\s*$)/);
  if (!match) return null;
  try {
    return JSON.parse(match[1].trim());
  } catch {
    return null;
  }
}
