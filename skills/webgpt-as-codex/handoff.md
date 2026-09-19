# Handoff

A handoff prompt is generated from:
- current project state;
- latest stage closure;
- current Git branch/HEAD;
- current runtime evidence that materially matters;
- unresolved risks;
- protected Experience Ledger rules.

It is not a copy of the previous prompt with a new stage number.

## Before handoff
- update all affected docs;
- write exact CURRENT/NEXT/AFTER_NEXT;
- verify prompt file exists locally;
- include explicit do-not-redo scope.

## Automatic continuation
Only when authorized:
1. prefer Playwright for the web UI;
2. enter the exact prompt;
3. submit once;
4. verify the submission actually occurred;
5. verify the new conversation/run has started;
6. then record handoff success.

A filled textbox, clicked button or URL change alone is not proof of successful handoff.
