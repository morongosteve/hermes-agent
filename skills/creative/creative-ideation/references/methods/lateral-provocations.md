# Lateral Provocations

**One line:** Make a deliberately false, absurd, or impossible statement about the problem, then use it as a stepping stone to a real idea.

**Invented by:** Edward de Bono (*Lateral Thinking*, 1967; the "PO" operation).

## When to use

- Mood signal: "make it weird", "less obvious", "too safe".
- High-slop terrain (AI apps, startups, wellness) where the obvious answer dominates.
- You've generated reasonable ideas and they're all boring.

## The method

A **provocation** (de Bono marks it "PO", meaning *provocative operation*) is a statement you don't believe, held just long enough to see where it leads. The point isn't the statement — it's the **movement** away from the stuck centre.

Four ways to generate a provocation:

1. **Reversal** — flip the normal direction. "The customer pays *us* to take the product back."
2. **Exaggeration** — push a number past reason. "A meeting with 10,000 people." "A book with one word per page."
3. **Distortion** — change a relationship. "The review is written *before* the product exists."
4. **Wishful** — state the impossible wish. "The car finds parking by itself and the street rearranges around it."

Then **extract movement** — don't judge the provocation, move from it:
- What's the *principle* buried in it?
- What's the *good* part if it were true?
- What *moment* does it make you picture?
- What's it *adjacent* to that is real?

## Worked example

Prompt: "give me a weird idea for a note-taking app."

- PO: **"The app deletes your notes after you read them."**
- Movement: impermanence forces you to *act* on a note, not hoard it → an idea: a notes app where each note has a visible "decay timer"; writing it down starts a countdown, and the only way to keep it is to *do* the thing or rewrite it. Hoarding is designed out.
- Grounded version: a 200-line CLI `jot` that appends timestamped notes to a file and, on read, shows how many days until auto-archive; rewriting resets the clock.

## Output shape

State the provocation explicitly ("PO: …"), then the movement, then the real idea it produced. Show the stepping-stone — it's half the value and it teaches the user the move.

## Pairs well with

`pataphysics` (push the strangeness further), `jobs-to-be-done` (provoke the *solution* after framing the real job).
