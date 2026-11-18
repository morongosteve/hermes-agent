# Compression Progress

**One line:** The most interesting idea is the one that most *compresses* your model of the world — maximal learnable surprise.

**Invented by:** Jürgen Schmidhuber's formal theory of creativity, curiosity, and beauty (2006–2010): interestingness = the *rate* at which a learner's compression of the data improves.

## When to use

- Phase = SELECTING, specifically picking a **research question** or the **highest-upside** option among many.
- RESEARCH domain: "what's worth asking?"
- You have many directions and want the one that teaches the most.

## The idea

Pure randomness can't be compressed — it's just noise, not interesting. Fully known regularity is already compressed — boring. The sweet spot is a pattern you *don't yet* have but *could* learn: engaging with it shrinks your description of a whole swath of other things. That shrinkage — the **compression progress** — is the signal creativity chases. Beauty is the moment of compression; curiosity is the drive toward where more compression is available.

## The method

For each candidate idea/question, score three things:

1. **Surprise now** — how much does it violate your current model? (Zero = boring; total = noise.)
2. **Learnability** — can you actually build a better model of it with the effort available? (If not, it's noise *to you*.)
3. **Reach** — if you understood it, how many *other* things would also become simpler? (This is the real prize.)

Pick the candidate highest in **reach among the learnable-and-surprising**. That's the question whose answer compresses the most.

## Worked example

Three possible blog posts / studies:
- "Our users like dark mode" — low surprise, low reach. Skip.
- "Why do transformer models X?" — high surprise but, with your tools, maybe not learnable this quarter. Park it.
- "The three support tickets that each explain 40% of churn" — surprising, learnable from data you have, and understanding it compresses your whole retention model. **Pick it.**

## Output shape

For each candidate, a one-line score on surprise / learnability / reach, then the pick and *why its reach is largest*. Don't just rank — explain the compression.

## Pairs well with

`polya` (once you've picked the question, go solve it), `first-principles` (to estimate reach honestly).
