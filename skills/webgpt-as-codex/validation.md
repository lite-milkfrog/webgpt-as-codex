# Validation

Minimum full-system gates:
- repository tests and lint;
- secret scan;
- component manifest schema validation;
- discovery does not confuse installed/listening/healthy;
- each enabled local MCP passes initialize + tools/list;
- gateway lists namespaced tools from each enabled backend;
- at least one safe tool call passes through gateway for core categories;
- OAuth metadata, dynamic registration, PKCE code exchange and refresh path pass when enabled;
- remote edge reaches OAuth-protected gateway when enabled;
- Manager survives UI close without stopping runtimes;
- restart/recovery does not require chat memory;
- bootstrap dry-run is idempotent;
- no user-specific secret or private URL is tracked;
- README claims match verified evidence.
