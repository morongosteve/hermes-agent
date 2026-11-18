# SCAMPER

**One line:** Run seven transformation operators over an existing thing to generate variations.

**Invented by:** Bob Eberle (1971), building on Alex Osborn's idea-spurring checklists.

## When to use

- Phase = EXPANDING: the user has a base idea/product and wants variations ("what else", "more like this").
- You need breadth fast from a known starting point.

## The operators

Apply each to the existing thing; keep the surprising results.

| Letter | Operator | Prompt to ask |
|---|---|---|
| **S** | Substitute | What component/material/person/step could be swapped out? |
| **C** | Combine | What if you merged it with another product, feature, or audience? |
| **A** | Adapt | What else is like this? What could you borrow from another field? |
| **M** | Modify / Magnify / Minify | What if it were much bigger, smaller, louder, slower, more extreme? |
| **P** | Put to another use | Who else could use it? What's it good for that it wasn't built for? |
| **E** | Eliminate | What can you remove? What's the product with its main feature gone? |
| **R** | Reverse / Rearrange | What if you flipped the order, the roles, the direction? |

## The method

1. State the base thing in one concrete sentence.
2. Walk all seven operators, generating at least one idea each (don't stop at the first good one).
3. Discard the predictable; the **E** and **R** operators usually yield the most non-obvious results — mine those.
4. Pick the 3 strongest and give each a mechanism + failure mode.

## Worked example

Base: "a weekly email newsletter."

- **S**: substitute the author — readers write it collectively each week.
- **C**: combine with a voicemail line — the newsletter is also a number you call to hear it read.
- **A**: adapt the "advent calendar" — 24 issues that only unlock on their date.
- **M**: minify — one sentence, every day, nothing more.
- **P**: put to other use — the back-catalogue becomes a searchable zine/archive product.
- **E**: eliminate the archive — each issue self-destructs; present-only.
- **R**: reverse — readers submit questions; the "issue" is only answers, no prose.

Grounded pick: the daily one-sentence email (**M**) — a tiny cron + mail script, shippable in an afternoon.

## Output shape

A labeled pass (S→R) is fine, but don't hand back 7 equally-flat bullets; surface the 2–3 that clear the anti-slop bar and develop those.

## Pairs well with

`volume-generation` (quantity first, SCAMPER to mutate the pile), `oblique-strategies` (when SCAMPER feels mechanical).
