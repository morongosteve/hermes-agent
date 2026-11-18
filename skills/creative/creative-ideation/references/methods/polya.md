# Pólya's Method

**One line:** A four-phase discipline for cracking a known problem — understand it, plan, execute, look back — backed by a toolkit of heuristics.

**Invented by:** George Pólya (*How to Solve It*, 1945). The foundation of modern problem-solving heuristics.

## When to use

- RESEARCH or ARTIFACT domain: a **well-defined problem you need to solve** (not an open-ended "what should I make"). Math, algorithms, debugging, a research obstacle, any puzzle with a target.
- Use `compression-progress` to *choose* the problem; use Pólya to *solve* the chosen one.

## The four phases

### 1. Understand the problem
- What is the **unknown**? What is the **data**? What is the **condition** linking them?
- Can you restate it in your own words? Draw a figure? Introduce notation?
- Is the condition sufficient? Redundant? Contradictory?
Most failed solving is skipped understanding.

### 2. Devise a plan
Reach for a heuristic:
- **Analogy** — have you seen a related problem? A simpler analog?
- **Specialize** — try a tiny or extreme case.
- **Generalize** — solve a broader problem that's somehow easier.
- **Work backward** — start from the goal and reason toward the givens.
- **Decompose / recombine** — break into subproblems.
- **Auxiliary problem** — solve a helper that unlocks the original.
- **Restate** — can you solve it if you drop/relax a condition?

### 3. Carry out the plan
Execute each step, checking it's correct as you go. Don't conflate "I have a plan" with "it works."

### 4. Look back
- Check the result (does it satisfy the condition? a different method agree?).
- Can you **derive it differently**? See it at a glance?
- Can you **use the result or method** for another problem? (This is how solving compounds into skill.)

## Worked example

Problem: find a bug where a cache returns stale data intermittently.
1. **Understand:** unknown = the condition under which staleness appears; data = it's intermittent, worse under load. Restate: "under what interleaving does a read see a pre-write value?"
2. **Plan — specialize:** force the extreme case — hammer one key with concurrent read/write; **work backward** from "a stale read happened" to "the write hadn't propagated / the read hit a replica."
3. **Execute:** reproduce with a 2-thread test pinned to that key; observe read hitting a replica before replication.
4. **Look back:** the fix (read-your-writes consistency) and the *method* (force the extreme interleaving) both generalize to the next concurrency bug.

## Output shape

Walk the four phases explicitly for the user's problem, name the heuristic used in phase 2, and in "look back" extract the reusable method — that's the compounding value.

## Pairs well with

`first-principles` (when the problem's framing itself is wrong), `compression-progress` (pick which problem is worth solving).
