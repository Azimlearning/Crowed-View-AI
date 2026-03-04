---
name: writing-plans
description: Creates detailed, step-by-step implementation plans assuming the executor has zero context. Use when you have a spec or requirements for a multi-step task, before touching code.
---

# Writing Plans

## When to use this skill
- The user has finalized a design (e.g., via the brainstorming skill) and it's time to build an implementation plan.
- The user asks for an implementation plan or step-by-step guide before coding begins.
- You have a spec or requirements for a multi-step task and need to break it down into modular steps before execution.

## Workflow
- [ ] **1. Setup**: Ensure context is clear. Create a dedicated directory/worktree if applicable.
- [ ] **2. Write Header**: Start the plan with a standard header (Goal, Architecture, Tech Stack).
- [ ] **3. Break Down Tasks**: Define bite-sized tasks (2-5 minutes each) following TDD (Test-Driven Development) principles.
- [ ] **4. Specify File Paths**: Use exact path names for all files being created, modified, or tested.
- [ ] **5. Add Verifications**: Include exact commands to run and their expected visual/terminal outputs to verify each step.
- [ ] **6. Save Document**: Save the completed plan to `docs/plans/YYYY-MM-DD-<feature-name>.md`.
- [ ] **7. Execution Handoff**: Present handoff and execution options to the user.

## Instructions

Write comprehensive implementation plans assuming the executing engineer has zero context for the codebase. Document everything they need to know: which files to touch, exact code to write, testing to perform, and docs to check. Keep it DRY, adhere to YAGNI, enforce TDD, and require frequent small commits.

**Plan Document Header Template:**
```markdown
# [Feature Name] Implementation Plan

> **Note to Executor:** Execute this plan task-by-task, following testing and verification steps exactly.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

**Task Granularity:**
Each step should represent one discrete action taking 2-5 minutes. A typical complete task loop is:
1. Write the failing test.
2. Run it to make sure it fails (include command).
3. Implement the minimal code to make the test pass.
4. Run the tests and make sure they pass (include command).
5. Commit the code.

**Task Details Example Form:**
```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**
(Insert complete, minimal test code snippet)

**Step 2: Run test to verify it fails**
Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**
(Insert implementation code snippet)

**Step 4: Run test to verify it passes**
Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```

### Execution Handoff
After saving the plan, offer the execution choice to the user:
*"Plan complete and saved to `docs/plans/<filename>.md`. Would you like me to start executing this plan now using the `executing-plans` skill, or do you want to review it first?"*

## Resources
- [Plan Execution Skill](executing-plans)
