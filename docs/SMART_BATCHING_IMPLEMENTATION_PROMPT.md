# Smart Batching Implementation Prompt

Use this prompt to start a new Claude Code session for implementing the smart batching feature:

---

Review the smart batching plan at F:\Art\cosmos-houdini-experiments\docs\SMART_BATCHING_PLAN.md and analyze the existing codebase to prepare for TDD implementation. Ultrathink about the architecture, potential challenges, and how to deliver maximum value with minimal complexity.

Focus areas for review:
- SimplifiedQueueService and how smart batching integrates as a non-invasive overlay
- Existing batch_inference capabilities in CosmosAPI
- Current UI patterns in jobs_ui.py for adding the smart batch controls
- Database models and queue management patterns

Remember: This is a solo developer project. Prioritize simplicity, working code, and the core 2-5x performance improvement. The feature must have zero impact when not in use.

Start by writing Phase 1 tests that define the essential behavior, then proceed with implementation following TDD principles.

---

This prompt encourages thorough analysis while maintaining focus on pragmatic, simple implementation.