# Feature: Template Project Automation

## Goal

Reduce the manual work required when creating a new project from this GitHub template. Currently, renaming from `my-project`/`my_project` to a new project name requires editing 15+ files manually.

## Problem Statement

When a user creates a new repo from this GitHub template, they must manually:

1. Rename `src/my_project/` directory to their package name
2. Update `pyproject.toml` (name, description, author, URLs, package paths)
3. Update `Makefile` (coverage path, docker image name, CLI commands)
4. Update `Dockerfile` (health check import, CMD, labels)
5. Update `docker-compose.yml` (coverage path, volume name)
6. Update `.github/workflows/test.yml` (CLI command, docker tag)
7. Update all Python files (import statements)
8. Update all test files (import statements)
9. Update `.claude/CLAUDE.md` (project description)

This is error-prone and tedious.

## Research: Compare with RolnickLab Template

**TODO:** Review and compare approaches used in:
- https://github.com/RolnickLab/lab-uv-template

Key questions to answer:
- How do they handle project name substitution?
- Do they use Copier, Cookiecutter, or another templating tool?
- What's the user experience for creating a new project?
- What tradeoffs did they make?

## Options Analysis

### Option 1: GitHub Template + Copier

Use [Copier](https://copier.readthedocs.io/) for variable substitution after GitHub template creation.

**Implementation:**
```bash
# User flow after "Use this template" on GitHub:
git clone <new-repo>
cd <new-repo>
copier copy gh:mihow/project-template-claude . --data project_name=my-new-project
```

**Pros:**
- Full Jinja2 templating support
- Interactive prompts for project metadata
- Can update existing projects when template changes
- Modern Python standard for this use case

**Cons:**
- Requires extra step after repo creation
- Users need copier installed
- Two sources of truth (GitHub template + copier template)

### Option 2: Setup Script

Add a `scripts/setup-project.sh` script that does find/replace.

**Implementation:**
```bash
#!/bin/bash
set -e

NEW_NAME=$1
NEW_NAME_SNAKE=$(echo "$NEW_NAME" | tr '-' '_')

# Rename directory
mv src/my_project "src/$NEW_NAME_SNAKE"

# Replace in files
find . -type f \( -name "*.py" -o -name "*.toml" -o -name "*.yml" -o -name "*.yaml" -o -name "Makefile" -o -name "Dockerfile" \) \
  -exec sed -i '' "s/my-project/$NEW_NAME/g" {} \;
# ... more replacements
```

**Pros:**
- No external dependencies
- Single command after clone
- Easy to understand

**Cons:**
- Fragile with special characters in names
- Platform-specific (sed -i differs on macOS vs Linux)
- Limited flexibility for complex substitutions

### Option 3: GitHub Actions Workflow

Add a workflow that runs on repo creation to auto-configure.

**Implementation:**
- Use `workflow_dispatch` or detect first push
- Read repo name from `${{ github.repository }}`
- Run setup script and commit changes

**Pros:**
- Fully automated after "Use this template"
- No local tooling required

**Cons:**
- Complex to implement correctly
- Can't easily prompt for additional metadata (author, description)
- Commits appear as bot, not user

### Option 4: Documented Manual Process

Keep current approach but document steps clearly with a checklist.

**Pros:**
- Simple, no tooling
- Users learn the codebase structure
- No maintenance burden

**Cons:**
- Error-prone
- Tedious for frequent template users

## Recommendation

**Short-term:** Add a setup script (Option 2) for immediate improvement.

**Long-term:** Evaluate Copier (Option 1) after researching RolnickLab's approach. Copier is becoming the standard for Python project templates and supports template updates.

## Requirements

- [ ] Research RolnickLab/lab-uv-template approach
- [ ] Decide on approach (script vs Copier vs hybrid)
- [ ] Implement chosen solution
- [ ] Update README with setup instructions
- [ ] Test with a new project creation
- [ ] Document any limitations

## Testing

1. Create a new repo from the template
2. Run the setup process with a test project name
3. Verify `make ci` passes
4. Verify GitHub Actions workflow passes
5. Verify CLI works: `new-project-name info`

## References

- [Copier documentation](https://copier.readthedocs.io/)
- [Cookiecutter](https://cookiecutter.readthedocs.io/) (older alternative)
- [GitHub Template Repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
- [RolnickLab UV Template](https://github.com/RolnickLab/lab-uv-template) - **TODO: Review**
