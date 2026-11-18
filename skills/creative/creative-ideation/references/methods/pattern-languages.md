# Pattern Languages

**One line:** Capture recurring solutions as named patterns — each a "context → problem → solution" — that compose with one another into a coherent whole.

**Invented by:** Christopher Alexander (*A Pattern Language*, 1977; *The Timeless Way of Building*). Adapted to software by the "Gang of Four" (*Design Patterns*, 1994) and the broader patterns community.

## When to use

- ARTIFACT domain, software architecture or any design with **recurring structure**.
- You keep solving the same shape of problem ad hoc and want a reusable, composable vocabulary.
- Designing a system where parts must fit together coherently (not just one clever component).

## The idea

A pattern names a solution that recurs, so you can invoke it by name and combine it with others. Alexander's deeper claim: patterns form a *language* — they reference and require each other, and a good design is a grammatical sentence in that language, not a pile of isolated tricks. Each pattern has the same skeleton: **a context**, **a problem (with its forces/tensions)**, and **a solution that resolves those forces** — plus links to the patterns above and below it in scale.

## The method (to *generate* with patterns)

1. **Name the forces.** What tensions must the design resolve? (latency vs. consistency; flexibility vs. simplicity; privacy vs. personalization.)
2. **Recall or coin patterns** that resolve each force, each as context→problem→solution. Reuse known ones (e.g. *Circuit Breaker*, *Bulkhead*, *Event Sourcing*, *Sidecar*; or Alexander's *Light on Two Sides of Every Room*).
3. **Compose, mind the links.** Patterns constrain each other — choosing one implies others and forbids some. Lay out which patterns call which.
4. **Check the whole reads coherently** — does the set of patterns make one thing, or a committee of clever parts?
5. **Coin a new pattern** when you hit a recurring problem with no name — context, forces, solution, and its place in the language.

## Worked example

Designing a flaky third-party integration layer. Forces: *reliability vs. responsiveness*, *isolation vs. shared resources*.
- Patterns composed: **Circuit Breaker** (stop hammering a failing service) + **Bulkhead** (isolate its thread pool so its failure can't drown the app) + **Cache-Aside with stale-while-revalidate** (stay responsive during outages).
- The links matter: Bulkhead makes Circuit Breaker safe to trip; the cache pattern defines what "open circuit" behavior the user sees. Together they're a small language for "depending on something unreliable."
- New pattern worth naming: *Graceful Degradation Ladder* — the ordered list of reduced-capability fallbacks as dependencies fail.

## Output shape

The forces, the named patterns with one-line context→problem→solution each, how they link, and any new pattern you coined. Favor a coherent small set over a long catalog.

## Pairs well with

`first-principles` (make sure a pattern is warranted, not cargo-culted), `triz-principles` (for component-level contradictions inside a pattern).
