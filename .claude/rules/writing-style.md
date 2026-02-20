---
paths:
  - "**/*"
---

# Writing Style

When writing PR descriptions, comments, or documentation: use a measured, factual tone. Describe actual changes rather than making broad claims. Avoid "comprehensive", "production-ready", "robust", "fully" unless objectively true.

## GitHub CLI

`gh pr edit` and some other `gh` commands emit a deprecation warning about "Projects (classic)" that causes exit code 1. Use `gh api repos/OWNER/REPO/pulls/NUM --method PATCH --field body="..."` for PR body updates instead.
