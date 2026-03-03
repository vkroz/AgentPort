---
status: done
---

# Implement `agentpack sync` Command

**Date:** 2026-03-02

## Context

`agentpack generate` is fully implemented. `agentpack sync` is a stub that prints "not yet implemented". The functional spec ([docs/functional-spec.md](../../docs/functional-spec.md)) has been updated to fully specify `sync` behavior, including the sync marker convention, conflict resolution rules, and remote config format.

## Problem

Users have no way to pull shared rule and skill sets from remote git repositories into their local `.agentpack/` directory. The `sync` command does not exist beyond a placeholder.

## Scope

**In scope:**
- Implement `agentpack sync` as specified in the functional spec
- Support the updated `remotes` config format (bare string URL or `{url, path}` object)
- Clone remotes to `~/.cache/agentpack/remotes/<name>/` on first run; pull on subsequent runs
- Merge remote `rules/*.md` into local `.agentpack/rules/`
- Merge remote `skills/<name>/` (including supplementary dirs) into local `.agentpack/skills/`
- Add sync marker to all synced files
- Delete local synced files (identified by marker) that no longer exist in the remote
- Conflict resolution: local files (no sync marker) always win; remotes processed first-to-last so later remotes override earlier ones
- Continue syncing remaining remotes if one fails; report all errors at the end
- Print informational message and exit 0 if no remotes are configured
- Update `generate` test coverage to verify it works correctly with synced content (SYNCED-marked files in `.agentpack/`)

**Out of scope:**
- `agentpack sync <name>` selective sync (sync always processes all remotes)
- Any GUI or interactive conflict resolution
- Merging across user/project/org/global hierarchy levels
- Any changes to `agentpack generate` logic (it already handles synced content correctly)

## Constraints and Assumptions

- Git must be available on `PATH`; sync delegates to `git clone` / `git pull`
- Remote repos use the same `.agentpack/` directory layout (configurable via `path`)
- Synced files are committed to the project repo (not gitignored)
- The sync marker format mirrors the generate marker convention:
  - With frontmatter: `# SYNCED BY agentpack. Remote: <name>` as YAML comment after opening `---`
  - Without frontmatter: `<!-- SYNCED BY agentpack. Remote: <name> -->` as first line
- Backward-compatible config: bare string remote values (just a URL) continue to work and use default `path: .agentpack`

## Acceptance Criteria

- [ ] `agentpack sync` with no configured remotes prints an informational message and exits 0
- [ ] `agentpack sync` clones a remote repo to `~/.cache/agentpack/remotes/<name>/` on first run
- [ ] `agentpack sync` pulls the remote on subsequent runs (no re-clone)
- [ ] Remote rules are copied into `.agentpack/rules/` with a sync marker
- [ ] Remote skills are copied into `.agentpack/skills/<name>/` (SKILL.md + supplementary dirs) with a sync marker on SKILL.md
- [ ] A local file without a sync marker is not overwritten (local always wins)
- [ ] A local skill directory whose SKILL.md has no sync marker is not overwritten (entire dir skipped)
- [ ] A file synced from remote A is overwritten by remote B when B appears later in the remotes list (B has higher priority)
- [ ] Remotes are processed in list order (first to last)
- [ ] A previously-synced file (with marker) that is removed from the remote is deleted locally on re-sync
- [ ] A previously-synced file (with marker) that is updated in the remote is updated locally on re-sync
- [ ] If one remote fails (unreachable), sync continues with remaining remotes and reports all errors at the end
- [ ] Both bare string (`community: https://...`) and object (`my-org: {url: ..., path: ...}`) remote config formats are parsed correctly
- [ ] After `sync`, running `agentpack generate` correctly incorporates synced rules and skills into tool-specific output

## Validation Steps

1. Configure a remote in `agentpack.yaml` pointing to a test git repo with `.agentpack/rules/` and `.agentpack/skills/`
2. Run `agentpack sync` — verify files appear in `.agentpack/rules/` and `.agentpack/skills/` with SYNCED markers
3. Run `agentpack sync` again — verify no re-clone occurs (pull only), no duplicate files
4. Manually remove a rule file from the remote repo and re-run `agentpack sync` — verify local synced file is deleted
5. Create a local rule with the same name as a remote rule (no sync marker) — verify sync skips it with a warning
6. Run `agentpack generate` after sync — verify synced rules appear in `.claude/rules/` or `.cursor/rules/` output
7. Configure a remote with custom `path` — verify rules are read from the correct subdirectory
8. Point a remote at an unreachable URL — verify sync reports the error and continues with other remotes

## Risks and Rollback

- **Risk:** Users running `agentpack sync` without git on PATH — mitigate with a clear error message
- **Risk:** Remote repo layout does not match expected structure — mitigate by silently skipping missing `rules/` or `skills/` dirs (not an error)
- **Rollback:** All synced files have markers and live in `.agentpack/` which is committed to git — reverting synced files is a standard git operation
