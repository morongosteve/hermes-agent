# Full Prompt Library — Constraint Dispatch

The default path when SPECIFICITY=NONE ("inspire me", "I'm bored", no domain). A **constraint** supplies traction; **direction** supplies shape. Pick ONE constraint that fits the user's hints (or at random if none), state it, then generate 3–5 ideas that obey it. Each idea gets a mechanism and a time/medium tag (see `SKILL.md` output format). Clear the `references/anti-slop.md` bar.

How to use: scan the section nearest the user's domain; if none, use **General**. Don't list the constraints to the user — *apply* one.

---

## General

Constraints that work in any domain.

- **The 100-year test.** Make something that would still work with no electricity / no internet.
- **One moving part.** The whole thing does exactly one thing, mechanically or conceptually.
- **For an audience of one.** Design it for a single named person (real or invented) and no one else.
- **It must be free and take under a minute to use.**
- **Combine two things you were told never to mix.** (A funeral and a game show. A spreadsheet and a love letter.)
- **Make the boring part the whole point.** Elevate the step everyone skips.
- **It has to fit in a shoebox** (or a tweet, or a single screen with no scroll).
- **Remove the most important feature** and see what the thing becomes.
- **Make it for the wrong season / wrong place / wrong time.**
- **The constraint is a number:** exactly 7 of something, or everything priced at $3, or 4 seconds long.

## Software / artifact

For software, hardware, mechanisms, tools.

- **Single-file, single-command.** A ~150-line script that does one surprising thing from the terminal.
- **No UI.** It runs as a cron job / a file watcher / a git hook and only speaks when something is true.
- **Local-first, no account, no server.** Everything lives on the user's machine.
- **The input is weird:** it takes your browser history / your shell history / your git log / your screenshots and makes one useful artifact.
- **Deliberately slow.** It refuses to answer for 24 hours on purpose. What becomes possible?
- **It talks to one existing thing** (an API, a device, a format) in a way its makers didn't intend.
- **Reverse a common tool.** A search engine that hides results; a to-do app that deletes tasks you don't do.
- **One keyboard shortcut** is the entire product.
- **It's a protocol, not an app.** Define the format; let anyone implement it.

## Physical / object

For visual art, sculpture, installation, physical making, craft.

- **One material only.** Everything from a single substance (paper, wire, salt, concrete).
- **It changes over time** — rusts, grows, fades, is eaten, melts — and that's the piece.
- **Site-specific:** it only makes sense in one exact location.
- **Human-scale inversion:** make the tiny huge or the huge tiny.
- **It requires the viewer to do something** (crouch, wait, return tomorrow, bring a friend).
- **Use a tool for the wrong job** (a sewing machine on metal, a 3D printer with clay).
- **Found material only** — nothing bought, everything salvaged.
- **It casts a shadow / makes a sound / smells** as the real content, not the object itself.

## Social / collective

For orgs, communities, civic projects, participatory work, events.

- **It only works if N strangers cooperate** — design for that dependency, not around it.
- **No leader, no center.** Any node can start it; it runs without anyone in charge.
- **The ritual is the product.** A repeatable thing people do together on a schedule.
- **Make the invisible visible** — surface a flow of money / attention / waste the community can't currently see.
- **Lower the cost of starting to near zero;** make quitting costless too.
- **It redistributes something** (attention, credit, surplus, risk) from where it pools to where it's scarce.
- **A small physical object** carries the whole social practice (a token, a stamp, a shared notebook).
- **Design for the person with the least power** in the system and let the rest follow.

## Lists (fast dispatch)

When you just need a spark, combine one from each column and build toward it:

| A — a verb | B — an unexpected noun | C — a constraint |
|---|---|---|
| map | your neighbors' wifi names | in under a minute |
| translate | the sound of your commute | with no screen |
| archive | every door you opened today | for someone who can't see |
| reverse | the last thing you threw away | using only what's in the room |
| amplify | a plant's water schedule | that works offline forever |
| ritualize | the pauses in a conversation | costing nothing |
| compress | a year of weather | that fits on a postcard |

Pick a row across (or mix columns), state the resulting seed as your constraint, and generate.

---

**After dispatch:** if the user bites on one idea, drop the library and switch to *building* it (SKILL.md rule 7). If they want variations on it, go to `references/methods/scamper.md`.
