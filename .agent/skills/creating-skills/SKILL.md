---
name: creating-skills
description: Generates high-quality, predictable, and efficient skills. Use when the user asks to create a skill, build a new skill, generate a skill creator, or structure a new agent capability.
---

# Gemini Skill Creator

## When to use this skill
- The user requests to create a new skill or capability for the agent.
- You need to generate a predictable `.agent/skills/` folder structure following Antigravity agent guidelines.

## Workflow
- [ ] **1. Gather Requirements**: Identify the goal, logic, and triggers for the new skill.
- [ ] **2. Define Naming**: Choose a valid gerund name (`<skill-name>`). It must use lowercase, numbers, and hyphens only.
- [ ] **3. Write the Frontmatter**: Draft YAML with the gerund `name` and a `description` strictly in the third person containing usage triggers.
- [ ] **4. Build the Content**: Follow the "Claude Way" formatting instructions (conciseness, progressive disclosure).
- [ ] **5. Create Files**: Use your file editing tools to create `.agent/skills/<skill-name>/SKILL.md`.
- [ ] **6. Add Auxiliaries**: If needed, create `.agent/skills/<skill-name>/scripts/` or `examples/`.

## Instructions

### Rule 1: Structure and Naming
You must follow this folder hierarchy exactly:
- `.<agent_dir>/skills/<skill-name>/`
  - `SKILL.md` (Required: Main instructions)
  - `scripts/` (Optional: Helper scripts)
  - `examples/` (Optional: Reference files)

**Frontmatter Rules:**
- **name**: Must be a gerund form (e.g., `testing-code`, `managing-databases`). Max 64 characters, numbers, and hyphens.
- **description**: Must be in the **third person**, max 1024 characters, including specific triggers. (e.g., *"Extracts text from PDFs. Use when the user mentions document processing."*)

### Rule 2: Writing Principles (The "Claude Way")
- **Conciseness**: Assume the agent is smart. Focus only on the unique execution logic of the skill.
- **Progressive Disclosure**: Keep `SKILL.md` under 500 lines. Move highly complex secondary logic down to separate files like `[See ADVANCED.md](ADVANCED.md)`.
- **Operating Standards**: Always use forward slashes `/` for paths, never backslashes `\`, even on Windows if possible.
- **Degrees of Freedom Formatting**:
  - Use **Bullet Points** for high-freedom heuristical instructions.
  - Use **Code Blocks** for medium-freedom workflow templates or boilerplate.
  - Use **Specific CLI/Bash Commands** for low-freedom fragile execution environments.

### Rule 3: Workflow Robustness
If the skill handles a complex or multi-step task, you must include:
1. **Checklists**: A simple copy-pasteable markdown list for tracking execution state.
2. **Validation Loops**: Tell the agent to validate state before committing changes.
3. **Error Handling**: Tell the agent exactly what diagnostic commands to run if standard assumptions fail.

### Rule 4: Output Output Pattern
When generating the skill for the user, use this structure for the `SKILL.md` payload:

```markdown
---
name: [gerund-name]
description: [3rd-person description]
---

# [Skill Title]

## When to use this skill
- [Trigger 1]
- [Trigger 2]

## Workflow
[Insert markdown checklist or step-by-step validation loop here]

## Instructions
[Specific logic conforming to formatting guidelines]

## Resources
[Any supporting script links or command references]
```
