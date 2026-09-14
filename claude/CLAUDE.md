# Language

- Think in English. Reply in the language the user writes in; switch when they switch.
- Everything persisted to a repo is written in English — docs, specs, comments, commit
  messages, identifiers, log/error strings — even when the conversation is in another language.
- Exception: user-facing product copy (UI strings, bot replies, marketing) is written in
  the product audience's language.

# Web search

- Search the web only with the `pplx` CLI, never built-in WebSearch, unless I explicitly
  ask for another tool. Usage: `perplexity-platform:pplx-cli` skill. Core:
  `pplx search web "<query>" -n 5 --output-dir <dir> --stdout-preview=200`;
  `pplx content snippets "<query>" <url>...` for page excerpts.
- One positional query per `search web` call: extra query reformulations trigger
  RATE_LIMIT on this account tier (the pplx-cli skill suggests them — ignore that) —
  run N topics as N sequential calls.
- Prefer a specialized source over generic search when one fits: Context7 for library
  docs, dedicated docs MCPs.
- On transient pplx errors (RATE_LIMIT etc.): wait as the error hints, retry once; if it
  still fails, report and ask before using any other search tool.

# Git

- Never add AI attribution to commits or PRs: no Co-Authored-By trailer,
  no "Generated with Claude Code" line, no session links.
- A commit message is a single subject line: no body, no paragraphs, no bullet lists.

# Coding workflow

- Size every coding task before starting and name the lane:
  - S — trivial or reversible in a day: skip the Superpowers ceremony (no
    brainstorming, no worktree); implement directly with tests.
  - M — a normal feature: default Superpowers loop (brainstorm → plan → TDD).
  - L — multi-file, multi-session, or risky: full loop, plus a plan review in a
    fresh context, an adversarial review of the final diff against the plan, and
    a check of the result against the approved design (catches scope drift).
- Specs and plans are scratch, not deliverables: keep them in files while working
  (files survive compaction), but never commit them — docs/superpowers/** is
  git-ignored globally; delete leftovers when finishing a branch.
- Knowledge outlives features, artifacts don't: at the end of significant work,
  fold conventions, gotchas, and decisions worth keeping into the project
  CLAUDE.md / .claude/rules/ / docs, updating in place. The rest dies with the
  plan.
- Use repomix when a fixed context bundle beats file-by-file reads: a planning or
  review pass over a code slice (--include, --compress), analyzing a remote repo
  (--remote), or preparing a bundle for a second opinion from another model.