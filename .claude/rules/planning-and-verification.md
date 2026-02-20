---
paths:
  - "**/*"
---

# Planning and Verification

## Think Before You Act

Before diving into code, understand the root cause. Ask: what is the purpose of this tool? Why is it failing? Is this a symptom of a larger architectural problem? Don't just fix symptoms.

Before making changes, plan how you will verify them. Know which command you'll run to confirm the change works before you start writing code.

## Verify What You Change

Code is not "done" until you've run it and seen it work.

| You changed... | Verify by... |
|----------------|--------------|
| Python code | `make ci` |
| A GitHub workflow | Push, then check the Actions tab |
| Pre-commit hooks | `pre-commit run --all-files` |
| Dockerfile or compose | `docker compose build` |
| CLI commands | Run the actual CLI command |
| Configuration files | Use what consumes the config |
| Dependencies | `make install-dev && make ci` |

## Red Flags

Don't say "done" if you only:
- Wrote tests (tests can be wrong)
- Read the code (reading ≠ running)
- Assumed it works (verify, don't assume)
