---
name: writing-plans
description: Creates detailed, step-by-step implementation plans assuming the executor has zero context. Use when you have a spec or requirements for a multi-step task, before touching code.
---

# Writing Plans

## Overview
Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, and how to test it. Provide bite-sized tasks that follow DRY, YAGNI, TDD, and frequent commit patterns.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Workflow
- [ ] **1. Scope Check**: If the spec covers multiple independent subsystems, suggest breaking it into separate plans — one per subsystem. Each plan must produce working, testable software on its own.
- [ ] **2. File Mapping**: Before defining tasks, map out which files will be created or modified. Design units with clear boundaries and well-defined interfaces.
- [ ] **3. Write Header**: Start the plan with a standard header (Goal, Architecture, Tech Stack).
- [ ] **4. Break Down Tasks**: Define bite-sized tasks (2-5 minutes each) following TDD principles.
- [ ] **5. Specify File Paths**: Use exact path names for all files being created, modified, or tested. Include complete code snippets for tests and minimal implementations.
- [ ] **6. Add Verification**: Include exact commands to run and their expected visual/terminal outputs to verify each step.
- [ ] **7. Save Document**: Save the completed plan to the specified directory.
- [ ] **8. Execution Handoff**: Present handoff and execution options to the user.

## Instructions

### Rule 1: Task Granularity
Each step represents one discrete action taking 2-5 minutes. A typical complete task loop is:
1. Write the failing test.
2. Run it to make sure it fails (include command).
3. Implement the minimal code to make the test pass.
4. Run the tests and make sure they pass (include command).
5. Commit the code.

### Rule 2: Plan Header Template
**Every plan MUST start with this header:**
```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if available) or executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Rule 3: Task Structure template
```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**
(Insert complete, minimal test code snippet)

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**
(Insert implementation code snippet)

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**
(Insert exact git command with descriptive message)
```

## Execution Handoff
After saving the plan, offer the execution choice to the user:
*"Plan complete and saved to `docs/plans/<filename>.md`. Would you like me to start executing this plan now using the `executing-plans` skill, or do you want to review it first?"*

## Resources
- [Plan Execution Skill](executing-plans)
- [Superpowers Skills](https://github.com/obra/superpowers/tree/main/skills)
- [Everything Claude Code](https://github.com/affaan-m/everything-claude-code)
- [Antigravity Awesome Skills](https://github.com/sickn33/antigravity-awesome-skills/tree/main/skills)
