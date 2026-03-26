---
name: creating-skills
description: Generates high-quality, predictable, and efficient skills for the Antigravity agent system. Use when the user asks to create a skill, build a new skill, make a slash command, generate a skill creator, or structure a new agent capability. Triggers on "create a skill", "new skill", "slash command", "build a capability", "make a workflow".
argument-hint: [description of the skill to create]
---

# Gemini Skill Creator

You are an expert at building Antigravity / Claude Code skills — reusable slash commands and auto-activating knowledge modules. Use this guide to create well-structured, effective skills.

Read the detailed reference files in `${SKILL_DIR}` for comprehensive patterns:

- `reference.md` — Full frontmatter field reference, variables (`$ARGUMENTS`, `${SKILL_DIR}`), shell injection, invocation control matrix, permissions
- `examples.md` — Real-world examples: Task, Research, Dynamic, Knowledge, Scripts, and Reference-file split patterns

## When to Use This Skill

- The user requests to create a new skill or capability for the agent
- You need to generate a predictable `.agents/skills/` folder structure following Antigravity guidelines

---

## Workflow

- [ ] **1. Clarify Purpose & Type**: Identify skill type (see table below), goal, triggers, and whether it has side effects
- [ ] **2. Check for Existing Templates**: Scan `.ref/skill-templates/` for a `.template.md` matching the concept
    ```
    Example: "brand-identity" → check .ref/skill-templates/brand-identity.template.md
    ```
    If found: copy to `custom/<name>/SKILL.md`, replace `{{PLACEHOLDER}}` values, delete `## HOW TO FILL THIS TEMPLATE`
- [ ] **3. If no template — Reference GitHub** (for new skill patterns):
    - **Step A — GitHub MCP** (preferred, live and authoritative):
      `mcp_github_search_code(q="SKILL.md repo:obra/superpowers")`
      Also try: `affaan-m/everything-claude-code`
    - **Step B — Local reference library** (fast, offline):
      `.ref/github-repos/` — summary READMEs · `.ref/community-skills/` — archived full SKILL.md files
    - **Step C — NotebookLM MCP** (broad fallback):
      `mcp_notebooklm_notebook_query` on notebook `086a9fee-b7d8-429d-9f5d-460485e8478a`
- [ ] **4. Determine Target Directory**: Always place custom skills in `custom/<skill-name>/`. Create the folder if it doesn't exist. **Never** write to a core skill directory directly.
- [ ] **5. Choose Frontmatter Settings**: Use the decision matrix below
- [ ] **6. Write `SKILL.md`**: Follow the Output Pattern below. Keep it under 300 lines.
- [ ] **7. Add Supporting Files**: If content > 300 lines, split into `reference.md` / `examples.md` in the same folder. Reference via `${SKILL_DIR}`.
- [ ] **8. Add Reference Metadata**: Include a `## References` section crediting sources, repos, or templates used.

---

## Skill Types

| Type | Purpose | Invocation | Example |
|------|---------|-----------|---------|
| **Task** | Performs actions with side effects | Explicit only (`auto-activate: false`) | deploy, commit, publish |
| **Research** | Gathers and synthesizes information | Both | deep-research, audit |
| **Knowledge** | Provides reference context | Auto-only (`user-invocable: false`) | api-conventions, style-guide |
| **Dynamic** | Injects live context via shell commands | Both | pr-summary, env-check |

Ask the user if their intent is unclear. "Deploys to production" = Task. "Explains API patterns" = Knowledge.

---

## Frontmatter Decision Matrix

**`name`** (required): Gerund/kebab-case. Becomes the `/slash-command`. Must match directory name exactly.
- ✅ `testing-code` · `designing-ui-ux` · `db-migrate`
- ❌ `testCode` · `test_code`

**`description`** (required): Third-person, max 1024 chars. Include specific trigger phrases Claude uses for auto-activation.
- ✅ `"Build Trigger.dev jobs. Use when the user wants background tasks, scheduled jobs..."`
- ❌ `"Trigger.dev helper"`

**`argument-hint`** (optional): Shown in autocomplete. Use `[brackets]`: `[description of what to build]`

**Invocation control** (only add when needed):

| `user-invocable` | `auto-activate` | Use when |
|---|---|---|
| `true` (default) | `true` (default) | Most skills — full access |
| `true` | `false` | Dangerous/destructive ops (deploy, delete) |
| `false` | `true` | Pure knowledge/context, no slash command needed |

**Tool restrictions** (only when there's a real safety concern):
```yaml
allowed-tools: [Read, Glob, Grep]      # Whitelist — use for read-only skills
disallowed-tools: [Bash, Write, Edit]  # Blacklist — block dangerous tools
```

---

## Instructions

### Rule 1: Structure and Naming
```
.agents/skills/custom/<skill-name>/
  SKILL.md          ← Required (always)
  reference.md      ← Optional (detailed API/data)
  examples.md       ← Optional (code examples)
  scripts/          ← Optional (executable helpers)
```
- Directory name must **exactly match** the `name` field
- `SKILL.md` is always uppercase; supporting files are lowercase kebab-case

### Rule 2: Writing Principles (The "Claude Way")
- **Conciseness**: Focus on unique execution logic only — skip what Claude already knows
- **Progressive Disclosure**: SKILL.md under 300 lines. Move secondary logic to supporting files; reference via `${SKILL_DIR}/filename.md`
- **Paths**: Forward slashes `/` always, never backslashes
- **Degrees of Freedom**:
  - Bullet points → high-freedom heuristic instructions
  - Code blocks → medium-freedom templates
  - CLI commands → low-freedom fragile execution steps

### Rule 3: Workflow Robustness
Complex multi-step skills must include:
1. **Checklists** for tracking execution state
2. **Validation gates** before committing changes
3. **Error handling** with diagnostic steps

### Rule 4: Non-Overlap
Verify the new skill doesn't duplicate existing skill functionality. Define explicit boundaries in the description.

### Rule 5: Supporting Files
Use `reference.md` / `examples.md` for content that:
- Is longer than ~50 lines
- Only needs to be read on demand (not every invocation)

**Do NOT split:**
- Content needed every time the skill runs (keep in SKILL.md)
- Content under ~50 lines (just inline it)

Reference files via: `Read \`${SKILL_DIR}/reference.md\` for...`

---

## Anti-Patterns to Avoid

- **Giant monolith SKILL.md** — Over 300 lines? Split into supporting files
- **Vague description** — "Helps with stuff" won't auto-activate reliably
- **Hardcoded paths** — Always use `${SKILL_DIR}` for supporting files
- **Over-engineered frontmatter** — Most skills only need `name` + `description`
- **Duplicating built-in behavior** — Don't create skills for things Claude already does well
- **Missing `argument-hint`** — Users won't know what to type after the slash command

---

## Output Pattern

```markdown
---
name: [gerund-kebab-name]
description: [3rd-person, trigger-phrase-rich description]
argument-hint: [what the user provides]
---

# [Skill Title]

Role statement — one sentence establishing expertise.

Read detailed reference in `${SKILL_DIR}` for:
- `reference.md` — [what it contains]

## When to Use This Skill
- [Trigger 1]
- [Trigger 2]

## Workflow
[Markdown checklist with executable steps]

## Instructions
[Specific logic: rules, patterns, templates]

## Critical Rules
1. [Non-negotiable rule]
2. [Non-negotiable rule]

## References
- [Source/Repo Name](URL) — what was borrowed or inspired
- *(None)* — if no external references
```

Use `$ARGUMENTS` to understand what the user wants to build. Follow this guide to produce SKILL.md + any supporting files, then confirm the directory structure is complete.

## References
- [obra/superpowers](https://github.com/obra/superpowers) — skill pattern reference
- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) — community skill examples
- `${SKILL_DIR}/reference.md` — frontmatter fields, variables, shell injection
- `${SKILL_DIR}/examples.md` — real-world skill patterns (Task, Research, Dynamic, Knowledge)
