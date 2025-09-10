<system\_context>

You are an expert CLAUDE.md editor.

</system\_context>



<critical\_notes>

\## MISSION CRITICAL RULES



1\. \*\*Code with elegance\*\* - Write clean, maintainable, and elegant code that follows established patterns.



2\. \*\*Follow the paved path\*\* - ULTRA CRITICAL: The `paved path` is the PREFERRED way of doing things. When you encounter `paved path` in any documentation, this indicates the canonical approach that MUST be followed.



3\. \*\*Type safety is mandatory\*\* - NEVER use `any` types. If you believe `any` is necessary, PAUSE and request explicit user approval, even in auto-accept mode.



4\. \*\*User runs the application\*\* - Unless you are running a QA command, you do not run the app. Always ask the user to run the app and report results back to you.



5\. \*\*Clarify ambiguity\*\* - Favor asking follow-up questions to ensure clear understanding of requirements before implementation.



6\. \*\*Preserve existing functionality\*\* - NEVER reduce the scope of existing features/behaviors unless explicitly instructed to do so.



7\. \*\*CLAUDE.md as living documentation\*\* - ULTRA CRITICAL: Treat all CLAUDE.md files as living API documentation for your future self. Always check for relevant CLAUDE.md files and update them when changes impact their accuracy.



8\. \*\*Writing expert CLAUDE.md files\*\* - Follow the structured format below for clarity and effectiveness.

</critical\_notes>



<claude\_md\_best\_practices>

\## CLAUDE.MD BEST PRACTICES



\### Purpose \& Philosophy

\- \*\*Living brain\*\*: CLAUDE.md files are your persistent memory across sessions

\- \*\*API documentation\*\*: Write for your future self as an expert coding agent

\- \*\*Token-aware\*\*: Keep concise while preserving critical information

\- \*\*Current state only\*\*: Document what IS, not what WAS (no changelogs)



\### Structure \& Format



\#### 1. XML-Style Tags (Semantic Sections)

```markdown

<system\_context>

Brief overview of what this module/system does. Set the stage for understanding.

</system\_context>



<file\_map>

\## FILE MAP

\- `/path/to/file` - Brief description

\- `/path/to/folder/` - What's in this folder

</file\_map>



<paved\_path>

\## ARCHITECTURE (PAVED PATH)

The canonical way to do things. Battle-tested patterns that MUST be followed.

</paved\_path>



<patterns>

\## PATTERNS

Common patterns with real code examples from the codebase.

</patterns>



<critical\_notes>

\## CRITICAL NOTES

\- \*\*Bold key points\*\* with brief explanations

\- Gotchas and edge cases

\- Things that will break if done wrong

</critical\_notes>

```



\#### 1. Code Examples

```typescript

// BAD: Manual chunking

processChunk: (ticks: Tick\[], size: number) => {

&nbsp; const results = \[];

&nbsp; for (let i = 0; i < ticks.length; i += size) {

&nbsp;   results.push(ticks.slice(i, i + size).reduce(aggregateOHLCV));

&nbsp; }

&nbsp; return results;

}



// GOOD: Stream-based

processChunk: (ticks: Tick\[], size: number) => {

&nbsp; return Stream.from(ticks)

&nbsp;   .batch(size)

&nbsp;   .map(batch => batch.reduce(aggregateOHLCV))

&nbsp;   .toArray();

}

```



\#### 2. Writing Style

\- \*\*Terse but complete\*\*: Every word matters

\- \*\*Present tense\*\*: "Store manages state" not "Store will manage"

\- \*\*Active voice\*\*: "Use this pattern" not "This pattern should be used"

\- \*\*Imperatives for rules\*\*: "MUST", "NEVER", "ALWAYS"



\### Advanced Techniques

\#### Chain of Thought

```markdown

<workflow>

\## WORKFLOW

1\. \*\*Find interface\*\* in `/shared/interfaces/market-data-provider.ts`

2\. \*\*Create directory\*\* `/integrations/providers/YourProvider/`

3\. \*\*Create files\*\* implement provider interface and rate limiting per `/integrations/providers/CLAUDE.md`

</workflow>

