<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Long-Running Output Capture Playbook

## The canonical pattern

For any command that takes more than a handful of seconds, **capture full output to a file, then read it back with `Read` or `Grep`**:

```bash
some-long-command > /tmp/cmd-output.log 2>&1
# then: Read /tmp/cmd-output.log     (or Grep for a specific pattern)
```

This is the shape every long-running invocation in this repo should take. The full transcript lives on disk; you can search it freely; you never have to re-run the command to recover output you already produced.

## Which commands this applies to

Commands that routinely run for many seconds to many minutes:

- `pytest`
- `./scripts/auto-pr`
- `./scripts/merge-pr`
- `./scripts/ci-debug`
- `python -m build`, `pip install`, and anything else that contacts the network or polls CI

When in doubt, capture. The disk is cheap; the context window is not.

## Anti-pattern: piping through `tail` / `head`

The shape to avoid is `<long-running-command> | tail -N` (or `| head -N`) as the *primary* capture method. The pipe buffers, the truncation destroys whatever the failure mode left earlier in stdout, and re-running the command to recover the lost lines is pure waste. Use the canonical pattern above instead.

(Note: `| tail -N` on a *cheap* command like `git log --oneline | tail -5` is fine — the rule is about long-running commands where re-running is expensive.)

## Anti-pattern: polling for process state

A reflex when waiting for a long-running command to finish:

```bash
while pgrep -f "python -m pytest" > /dev/null; do sleep 30; done
```

This loop **never exits** — `pgrep -f` matches against the full command line of every process, and the bash running the wait-loop has the literal string `python -m pytest` in its own argv. The loop self-matches and waits for itself forever. Same trap class as `ps aux | grep foo` (the `grep` self-matches in its own output).

**Standard workarounds:**

- **Match by PID.** Capture `$!` when starting the command, then poll `kill -0 $PID 2>/dev/null` (returns nonzero when the PID is gone). PIDs can't be self-matched.
- **The `[p]ytest` regex trick.** Write `pgrep -f "[p]ython -m pytest"`. The bracket-`p`-bracket is a regex character class matching `p`; the literal `[p]` in the wait-loop's argv has the brackets, which don't match the regex.

**Doctrine:** if you're reaching for `pgrep`, `ps | grep`, or any while-loop that polls process state, consider first that you might have other tools readily available that would do it without the trap.

## Reading the captured log

Use the `Read` tool on the file, or `Grep` for the pattern you care about. The log already has everything — re-running the command to "see what happened" produces nothing the file doesn't already contain.

## Quick self-check before running a long command

- Will the output fit on one screen? If no, **redirect to a file**.
- Will the output be useful if only the last 30 lines survive? If no, **redirect to a file**.
- Is this a command listed above under "Which commands this applies to"? If yes, **redirect to a file**.
- Do I plan to keep working while it runs? If yes, **run in background + monitor the file**.

When in doubt, redirect.
