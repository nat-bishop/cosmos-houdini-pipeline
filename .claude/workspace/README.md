# Claude Workspace - TEMPORARY DOCUMENTS ONLY

## ⚠️ CRITICAL RULE
**EVERYTHING in this directory is temporary and will be deleted when the task is complete.**

If a document needs to become permanent, MOVE it to the correct location:
- Architecture docs → `docs/architecture/`
- Development guides → `docs/development/`
- Scripts → `.claude/scripts/`
- Project docs → `docs/`

## 📝 Document Naming
Use descriptive names with dates:
- `tdd-implementation-2025-09-02.md` ✅
- `refactor-cli-notes-2025-09-03.md` ✅
- `scratch.md` ❌ (too vague)
- `todo.md` ❌ (too generic)

## 🔄 Lifecycle
1. **CREATE** - Make document in workspace for current task
2. **USE** - Update freely during work
3. **DECIDE** - When task done, either:
   - **DELETE** - Most common (task complete)
   - **MOVE** - Rare (became valuable permanent doc)

## 🧹 Cleanup Rule
At the end of each week or major task:
- Delete all completed task documents
- Move any valuable content to permanent locations
- Workspace should regularly return to near-empty

## 💡 Examples

### Task Document (Most Common)
```markdown
# TDD Implementation - 2025-09-02
Current task: Implement TDD workflow
[checkbox list of tasks]
[working notes]
→ DELETE when done
```

### Discovery Document (Occasionally Becomes Permanent)
```markdown
# GPU Memory Investigation - 2025-09-02
[research findings]
[benchmarks]
→ If valuable: MOVE to docs/architecture/gpu-memory-guide.md
→ Otherwise: DELETE
```

## ❌ What NOT to Put Here
- Permanent documentation
- Configuration files
- Scripts or code
- Anything you want to keep long-term

Remember: **Workspace = Temporary = Will Be Deleted**
