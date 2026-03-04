---
name: saving-progress
description: Saves the current project progress to the Git repository by securely checking for leaks, staging changes, writing a detailed commit message, and pushing to the main branch. ONLY invoke this skill when the user explicitly asks to save, commit, or push — NEVER auto-invoke during implementation.
---

# Saving Project Progress

<HARD-GATE>
Do NOT invoke this skill automatically. Do NOT commit or push at the end of a task, after a feature implementation, or as a "cleanup" step.
This skill runs ONLY when the user explicitly says one of:
- "save my progress"
- "commit this"
- "push to GitHub"
- Or a clearly equivalent explicit request.
If the user has not said one of these, do NOT run this skill.
</HARD-GATE>

## When to use this skill
- The user **explicitly** asks to "save progress", "commit changes", or "push to GitHub".
- The user has reviewed the changes themselves and decided they are ready to commit.
- **Never** invoke this automatically at the end of a plan, feature implementation, or verification step.

## Workflow
- [ ] **1. Security Check**: Run a validation to ensure no API keys (e.g., Google Maps API keys, credentials), sensitive endpoints, or `.env` files are accidentally being committed. Look through unstaged changes using `git diff`.
- [ ] **2. Git Add**: Stage all changes using `git add .`.
- [ ] **3. Analyze Changes**: Review the staged changes using `git diff --staged` to summarize what progress has been made.
- [ ] **4. Draft Commit Message**: Write a comprehensive, well-structured commit message detailing what was changed, added, or fixed.
- [ ] **5. Git Commit**: Commit the changes securely. If the message is long, create a temporary text file with the message and use `git commit -F <file>`, or use multiple `-m` flags.
- [ ] **6. Git Push**: Push the commit to the main branch using `git push origin main`.

## Instructions

### Rule 1: Security First
- Always double-check modifications in common potential leak points (e.g., `index.html`, `js` configuration files, `config.json`).
- If a hardcoded API key or private secret is detected in the diff, **STOP** and inform the user before committing. Do not push secrets!

### Rule 2: Detailed Commit Messages
- The commit message should not be a single generic line.
- It must clearly state the progress update.
- Provide a summary title followed by bullet points. 
- Example pattern:
  ```text
  [Update]: Implemented AI Assistant Page and Routing

  - Added new Assistant wizard routing in index.html
  - Updated chatbot script to support multi-step tool UI
  - Fixed typo in app-shell styling
  ```

### Rule 3: Git Commands
- Always confirm `git push origin main` works successfully. If it fails due to remote changes, report the error to the user and suggest `git pull --rebase` or similar safe merging.

## Validation Loop
1. Did you check for secrets in the diff before committing?
2. Did you write an accurate and detailed multi-line commit message?
3. Did the push to the main branch of `https://github.com/Azimlearning/Crowed-View-AI` succeed?

## Resources
- Target Repository: `https://github.com/Azimlearning/Crowed-View-AI`
- Branch: `main`
