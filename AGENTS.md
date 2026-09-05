# Repository Operational Rules for AI Assistants

## 1. Process Execution Rules (CRITICAL)
- **NEVER use asynchronous/background processes or manage_task for commands**.
- Always run terminal commands synchronously with `WaitMsBeforeAsync: 10000` and `RunPersistent: true`.
- If a command might produce long output, pipe it through `cat` or `--no-pager`. Never allow an interactive pager or prompt to block execution.

## 2. Mandatory Testing Before Every Commit
- **NEVER push or commit code without testing all Python files**.
- Always run compilation checks across the entire codebase:
  ```bash
  python3 -m compileall src/ scripts/ tests/
  ```
- Always run all relevant test suites:
  ```bash
  python3 -m unittest discover -s tests
  ```
- If dependencies or JSON configs are modified, validate them explicitly (e.g. `python3 -c "import json; json.load(open('portfolio_config.json'))"`).

## 3. GitHub Actions Verification
- Use GitHub CLI (`gh run list`, `gh api`) to monitor and verify workflow runs after triggering or pushing changes.
- Never leave broken workflow runs uninvestigated.
