# Cosmos Workflow Manager UI - Session Handover

Please thoroughly review the UI improvement plan located at `.claude/UI_IMPROVEMENT_PLAN.md` before proceeding with any implementation.

## Context
You're continuing work on the Cosmos Workflow Manager UI improvements. Several tasks have been completed (removing Select All button, applying consistent styling to Input Details, and partially removing model_type references). The remaining tasks are documented in the plan.

## Key Implementation Guidelines

### Testing Requirements
- Test EVERY change with Playwright browser automation
- Verify functionality works as expected before moving to the next task
- Commit changes frequently after each successful test
- Use `mcp__playwright__browser_*` tools for testing

### Technical Principles
- **Use CosmosAPI exclusively** - Never access the database directly, always use the CosmosAPI methods (get_prompt, list_runs, get_run, preview_run_delete, run_delete, etc.)
- **Avoid code duplication** - Reuse existing functions and components where possible
- **Follow existing patterns** - Match the code style and patterns already established in the codebase

### Design Principles
- **Visual Consistency**: Ensure all detail sections use the same structured textbox field styling
- **Hierarchy & Contrast**: Use visual weight and color to guide user attention
- **Micro-interactions**: Add hover states, smooth transitions, and loading indicators
- **User Safety**: Implement clear warnings and confirmations for all destructive actions (deletions)

### Priority Tasks
1. Complete the model_type removal from UI components
2. Add enhanced status indicator to Prompt Details
3. Combine and style Input Details with Video Previews
4. Redesign Output Details for better input→output visualization
5. Create the Run History tab with full run information
6. Implement deletion features with proper warnings using preview_run_delete and run_delete

### Quality Standards
- Don't hold back - give it your all
- Think deeply about user experience and visual design
- Apply professional design principles (hierarchy, contrast, balance, movement)
- Create an impressive demonstration of web development capabilities
- Analyze your results after each step to ensure correctness

Remember: The goal is to create a polished, professional UI that makes it easy to manage Cosmos Transfer workflows, view results, and make decisions based on inference outputs.