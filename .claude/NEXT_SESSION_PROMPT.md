# Continuation Prompt

## Project
Claude-first Python project template: https://github.com/mihow/project-template-claude

## What Was Done
- Created full template with .claude/ directory (CLAUDE.md, rules, skills, agents)
- MCP server config for chrome-devtools (headless) and Python LSP
- Verification-first approach with smoke tests and `/verify` skill
- Python 3.12+, uv, pytest, ruff, pyright, Docker, GitHub Actions
- Weekly docs checker workflow (.github/workflows/check-docs.yml)
- Best practices documentation in .claude/docs/

## CI Failures to Fix

These issues have been fixed in prior sessions.

## Key Files
- `.claude/rules/verification.md` - verification requirements
- `tests/test_smoke.py` - smoke tests that run CLI
