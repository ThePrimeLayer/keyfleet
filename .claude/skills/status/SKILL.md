---
name: status
description: Repo briefing — freshness check (offers a fast-forward pull), recent activity + next planned step
allowed-tools: Bash(git log:*), Bash(git status:*), Bash(git fetch:*), Bash(git ls-remote:*), Bash(git rev-parse:*), Bash(git rev-list:*), Bash(git diff:*), Bash(git pull --ff-only), AskUserQuestion, Read, Glob, Grep
disable-model-invocation: true
---

Read-only briefing. Do NOT edit, stage, commit, or push anything in this pass — orientation
and status only. The ONE exception is PHASE 0's fast-forward pull, and only after the owner
says yes to it in this session.

PHASE 0 — Freshness check (a stale checkout gives a stale briefing; do this before reading).
- Run: git status -sb, and note the first line: "[behind N]", "[ahead N]", both (diverged), or
  neither (in sync with origin/main as last fetched).
- Refresh the remote-tracking ref if this harness permits it, trying in order and stopping at the
  first that works: (a) git fetch --prune (it updates .git remote-tracking refs only); (b) git
  fetch --dry-run (network only, writes nothing); (c) git ls-remote --heads origin main, compared
  with git rev-parse origin/main. After (a), re-run git status -sb.
- If none of (a)-(c) can run, do not fail the briefing: report "freshness unverified" plus the
  last time origin/main was refreshed locally, from:
  git log -g -1 --date=iso --format='%gd | %gs' origin/main
- Lead section (1) with one line: local main <hash> vs origin/main <hash> (refreshed <time> /
  unverified) — behind N / ahead N / diverged / in sync.
- If behind or ahead, gather before deciding: the counts (git rev-list --left-right --count
  origin/main...HEAD → behind, ahead); the incoming commit subjects (git log --oneline
  HEAD..origin/main); the files they touch (git diff --name-only HEAD...origin/main); local
  uncommitted and untracked files (git status --porcelain); and the OVERLAP, the local files
  that the incoming commits also touch.
- Then act on the first case that fits. The fast-forward pull is the only command this skill
  may run, and only on a yes; every other command below is a recommendation, shown in full,
  for the owner to run or to approve after the briefing.
  (A) Behind, 0 ahead, clean tree: ask the owner (AskUserQuestion), naming the N incoming
      commits, whether to pull now with `git pull --ff-only`. On yes, run it, report the new
      local hash and re-run git status -sb, then continue on the pulled files. On no, continue
      read-only as in (E).
  (B) Behind, 0 ahead, uncommitted or untracked changes (work started before a status check):
      do not pull yet. List the local files, the incoming files, and the overlap.
      - No overlap: say the pull is safe (git keeps local edits it does not have to touch),
        then ask as in (A).
      - Overlap: recommend saving the local work first, then pulling and resolving only the
        overlapping files: either commit it (`git add <files>` + `git commit`, then
        `git pull --rebase`), or set it aside (`git stash push -u`, `git pull --ff-only`,
        `git stash pop`). Say which suits the size of the local work, and that a stash pop may
        stop on conflicts in the overlapping files. Do not run either; continue read-only (E).
  (C) Behind AND ahead (diverged: local commits not on origin): do not pull. List the local-only
      commits (git log --oneline origin/main..HEAD) and the overlap, then recommend by AGENTS.md
      §9: small changes → `git pull --rebase`, then push once the owner has reviewed the diff;
      anything that changes the ledger schema, a data-file format, or the CLI surface → move
      them to a `feat/<topic>` branch and open a PR (`git switch -c feat/<topic>`,
      `git push -u origin feat/<topic>`, then reset local main to origin/main only after the
      branch is safely pushed). Never force-push main. Continue read-only (E).
  (D) Ahead only: note the unpushed commits and recommend pushing or opening a PR per §9.
  (E) Read-only fallback (no pull made): read the remote-only commits read-only (git log --stat
      HEAD..origin/main; git log -p HEAD..origin/main -- <file>) so PHASES 1-3 reflect the
      current state, and say which conclusions came from remote-only content.

PHASE 1 — Orient and read the relevant files (do not blind-crawl the whole repo).
1. Read AGENTS.md (how to work here) and CLAUDE.md.
2. Read PLAN.md: milestones, open questions, and the session log (where the last agent stopped).
3. Read the "Unreleased" section and latest release of CHANGELOG.md, and docs/DECISIONS.md.
4. Consult keyfleet-BRIEF.md (what to build) by section only where PLAN.md or a milestone points
   to it (§7 data model, §8 CLI, §9 logic, §15 open decisions); read docs/ASSUMPTIONS.md only if
   a milestone depends on an assumption.

PHASE 2 — Catch me up on recent activity.
- Run: git log --oneline -12, and read the last few PLAN.md session-log lines.
- Run: git status --short, to surface uncommitted or untracked work that the log won't show;
  report it separately from committed history.
- If PHASE 0 found remote-only commits, include them marked "remote-only (not yet pulled)".
- Summarize what changed most recently and where each milestone stands. Cite the source for
  each point (PLAN.md line, CHANGELOG entry, or commit hash). Distinguish what is DONE (shipped
  per CHANGELOG/tags/git) from what is only planned or in progress.

PHASE 3 — Tell me the next step, per the plan itself.
- Derive the next actionable step from PLAN.md's milestones and open questions and the brief's
  scope. Do NOT invent a next step from your own judgment — cite where you found it.
- If several steps are eligible, list them and say which the plan prioritizes, and why.
- Flag any blocker (open question, owner decision per AGENTS.md §10, failing check) — surface
  it for me to decide rather than guessing.
- If any conclusion isn't grounded in a file you actually read, say so instead of asserting it.

Report format: (1) Recent activity & current state, (2) Next step(s) with plan citation,
(3) Blockers / open decisions. Keep it scannable. Make no changes beyond an approved
fast-forward pull.
