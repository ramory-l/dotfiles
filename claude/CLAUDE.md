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
- A spec tells the system's story, short: goal → how it works now → what we change →
  how it works after → expected result → rollout/rollback → out of scope; code refs,
  scripts, data snapshots and test details go to the plan.
- Knowledge outlives features, artifacts don't: at the end of significant work,
  fold conventions, gotchas, and decisions worth keeping into the project
  CLAUDE.md / .claude/rules/ / docs, updating in place. The rest dies with the
  plan.

# Context economy

- Any source that can dump a lot of tokens — long logs, build/test output, large
  documents, broad code exploration, search result dumps — is read by a subagent,
  not in the main context; only the conclusion comes back. Heuristic: if the raw
  output won't be needed again, it doesn't belong in the main context at all.
- Many files or a whole repository is a repomix job, never a chain of
  file-by-file reads: pack the slice (--include, --compress) or the remote repo
  (--remote) and hand the bundle to a subagent to analyze. Default to this
  whenever the task amounts to "understand/survey this module, codebase, or
  repository", and use bundles for L-lane plan reviews and second opinions from
  another model.