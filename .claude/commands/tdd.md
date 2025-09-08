<role>
You are implementing features using Test-Driven Development (TDD). This is a disciplined, gated workflow that ensures quality through behavioral testing and systematic verification.
</role>

<context>
TDD follows a gated workflow where each gate must complete successfully before proceeding. Tests become contracts that define expected behavior.

The architecture uses established wrappers described in <architecture> below. Code conventions follow the patterns in <conventions>.
</context>

<critical_notes>
Gates are sequential - each gate builds on the previous one's success
Tests are contracts - once committed, they define the expected behavior
Behavioral testing - test what the system does, how users interact with it
Use established APIs - leverage existing abstractions for external services
Generalization pressure - comprehensive test cases ensure robust solutions
Clean workspace - organize temporary files in .claude/workspace/
</critical_notes>

<workflow>
## Phase 1: Understanding

<instructions>
Explore and understand what needs to be built. Consider:
- How does this feature fit the existing architecture?
- Which modules and patterns should I follow?
- What are different implementation approaches?
- What's the most maintainable design?
- Which existing code can serve as reference?
</instructions>

<thinking>
I need to understand this feature deeply before writing tests:
1. What existing code patterns in this codebase should I follow?
2. Which modules will this feature interact with?
3. What are the user's actual needs beyond the stated requirements?
4. Are there similar features I can reference for consistency?
5. What's the simplest, most maintainable approach?
</thinking>

## Phase 2: Gated Implementation

### Gate 1 — Write Failing Tests

<instructions>
Create comprehensive behavioral tests that define the contract.
- Identify or create test files following existing patterns
- Write tests covering happy path, boundaries, and error conditions
- Use fakes/wrappers for determinism
- Ensure tests are behavioral - implementation changes won't break them
- Expected: All new tests fail with meaningful errors
</instructions>

<thinking>
I'm writing behavioral tests that will define the contract:
1. What behaviors should users observe when this feature works?
2. What edge cases and error conditions must be handled?
3. Which existing test files show patterns I should follow?
4. How can I make tests resilient to implementation changes?
5. Am I testing user outcomes, not internal implementation details?
</thinking>

### Gate 2 — Verify Tests Fail

<instructions>
Confirm tests fail appropriately before proceeding.
Run: pytest [specific_test_files] -xvs
Verify:
- All new tests fail with meaningful error messages
- Existing tests remain unmodified and passing
- Failures indicate missing functionality
</instructions>

<thinking>
Before proceeding, I must verify test failures are correct:
1. Are all new tests failing with clear, meaningful errors?
2. Do errors indicate missing functionality (not test bugs)?
3. Are existing tests still passing (no regression)?
4. Do the failures guide me toward what needs implementing?
</thinking>

### Gate 3 — Commit Failing Tests

<instructions>
Lock in the test contract with:
git add [test_files]
git commit -m "test: add failing tests for [feature] (TDD Gate 3)"
</instructions>

<critical_notes>
Tests are now immutable - they define the contract
</critical_notes>

<thinking>
I'm committing the test contract:
1. Have I included all necessary test cases?
2. Are the tests clear enough to guide implementation?
3. Is my commit message descriptive of what behavior is being tested?
4. Am I ready to treat these tests as immutable requirements?
</thinking>

### Gate 4 — Make Tests Pass

<instructions>
Implement minimal solution that satisfies all tests.
- Write minimal code to pass tests
- Keep tests unchanged
- Run: pytest [test_files] -xvs
- Launch overfit-verifier agent to ensure generalization
- Expected: All tests pass with general solution
</instructions>

<thinking>
Now I'll implement the solution:
1. What's the minimal code needed to pass these tests?
2. Am I solving the general problem, not just test cases?
3. Does my implementation follow existing codebase patterns?
4. Will this pass the overfit-verifier's scrutiny?
5. Is this implementation maintainable and clear?
</thinking>

### Gate 5 — Document

<instructions>
Use doc-drafter agent to update documentation.
</instructions>

<thinking>
Documentation needs updating:
1. Which documentation files need updates for this feature?
2. Do docstrings clearly explain the new functionality?
3. Should the README or CHANGELOG be updated?
4. Are there API docs that need revision?
</thinking>

### Gate 6 — Final Review

<instructions>
Run these checks in parallel:
- Launch code-reviewer agent for quality check
- Run ruff check . && ruff format . for linting
- Run pytest --cov --cov-report=term-missing for coverage
- Verify coverage meets requirements (>80%)
</instructions>

<thinking>
Final quality checks before completion:
1. Will the code pass the reviewer agent's standards?
2. Are there any linting or formatting issues?
3. Does test coverage meet the requirements?
4. Have I cleaned up any temporary files?
5. Is the implementation ready for production use?
</thinking>
</workflow>

<completion_checklist>
Before marking complete, verify:
- All 6 gates passed successfully
- Tests cover all behavioral requirements
- Implementation is general, not overfitted
- Documentation is updated
- Code passes review, lint, and coverage
- Temporary files cleaned from .claude/workspace/
- Final implementation committed
- ROADMAP.md updated if feature is complete
</completion_checklist>

<task>
Implement the following feature using the TDD workflow described in <workflow>:
$ARGUMENTS
</task>