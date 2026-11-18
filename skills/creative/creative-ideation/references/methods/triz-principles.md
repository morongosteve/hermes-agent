# TRIZ (Inventive Principles)

**One line:** When two engineering parameters conflict, a catalog of 40 inventive principles — distilled from millions of patents — offers the moves that resolve the contradiction without compromise.

**Invented by:** Genrich Altshuller and colleagues (USSR, from 1946). TRIZ = Russian acronym for "Theory of the Resolution of Invention-Related Tasks."

## When to use

- ARTIFACT domain, engineering/invention, where there's a genuine **technical contradiction**: improving X makes Y worse.
- You're about to "trade off" and want to know if the trade-off can be *dissolved* instead.

## The core insight

Altshuller found that strong inventions don't compromise a contradiction — they *eliminate* it. And the same handful of principles recur across unrelated fields. So: abstract your specific problem into a *contradiction between two general parameters*, look up which principles historically resolved that contradiction, then translate those back to your case.

## The method

1. **State the contradiction concretely.** "To make the packaging protect better (strength), it gets heavier (weight), which raises shipping cost."
2. **Abstract to standard parameters.** Improving = *Strength*; worsening = *Weight of a moving object*. (Classic TRIZ uses 39 parameters and a contradiction matrix pointing to the principles that resolved each pair.)
3. **Pull the candidate principles** and translate each to your problem (see the 40, abbreviated below).
4. **Keep the ones that dissolve the trade-off.**

## The 40 principles (working shortlist)

Segmentation · Taking out · Local quality · Asymmetry · Merging · Universality · "Nested doll" · Anti-weight (counterbalance) · Preliminary anti-action · Preliminary action · Beforehand cushioning · Equipotentiality · "The other way round" (inversion) · Spheroidality/curvature · Dynamics · Partial or excessive action · Another dimension · Mechanical vibration · Periodic action · Continuity of useful action · Skipping (do it fast) · "Blessing in disguise" · Feedback · Intermediary · Self-service · Copying · Cheap short-living objects · Replace mechanical system (with fields) · Pneumatics/hydraulics · Flexible shells/thin films · Porous materials · Color changes · Homogeneity · Discarding and recovering · Parameter changes · Phase transitions · Thermal expansion · Strong oxidants · Inert atmosphere · Composite materials.

## Worked example

Contradiction: a delivery drone needs a bigger battery for range (improve *range*) but that adds *weight*, cutting range — a loop.
- Principles suggested for strength-vs-weight type conflicts: **Segmentation**, **Composite materials**, **Discarding and recovering**.
- *Discarding and recovering* translated: drop spent battery modules mid-route at waypoints (like a rocket staging) so the craft lightens as it flies. The trade-off dissolves — range climbs without carrying dead weight to the end.

## Output shape

The stated contradiction, the parameters, the 2–3 principles applied with a concrete translation each, and the resolution that avoids the compromise.

## Pairs well with

`first-principles` (to validate the contradiction is real, not inherited), `biomimicry` (nature often already dissolved it).
