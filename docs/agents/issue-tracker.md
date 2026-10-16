# Issue tracker: Local Markdown

Issues for this repo live as markdown files in `.scratch/`. Specs live in `docs/spec/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `docs/spec/<feature-slug>.md` (for example `docs/spec/docs_qa.md`)
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Near the top of each issue file:
  - a `Spec:` line naming the spec and the sections it covers;
  - a `**Blocked by:** NN, NN` line;
  - a `**Status:**` line with the triage role string (see `triage-labels.md`), or `completed (<date>)` when done.
- The acceptance criteria are a `- [ ]` checklist, ticked when met
- Results, decisions and test runs go under a `**Notes:**` heading
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/issues/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly. "Issue 8"
means `.scratch/<feature-slug>/issues/08-*.md`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
