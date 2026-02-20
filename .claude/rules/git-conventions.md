---
paths:
  - "**/*"
---

# Git Conventions

- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` with optional scope: `fix(router): handle empty field`
- **Stage selectively**: Never use `git add -A` or `git add .` blindly. Use `git add -p` to selectively stage hunks. For agents: `printf 'y\nn\ny\n' | git add -p file.py`
- **Small, focused commits**: Easier to review and rollback
