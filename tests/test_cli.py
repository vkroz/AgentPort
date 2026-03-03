"""Tests for the CLI."""

from typer.testing import CliRunner

from agentpack.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_init_creates_directory_structure(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0

    ap_dir = tmp_path / ".agentpack"
    assert ap_dir.is_dir()
    assert (ap_dir / "rules").is_dir()
    assert (ap_dir / "skills").is_dir()


def test_init_creates_config_file(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])

    config = (tmp_path / ".agentpack" / "agentpack.yaml").read_text()
    assert "agents:" in config
    assert "claude" in config
    assert "cursor" in config
    assert "gitignore: true" in config


def test_init_creates_starter_claude_md(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])

    claude_md = (tmp_path / ".agentpack" / "rules" / "CLAUDE.md").read_text()
    assert "description:" in claude_md
    assert "alwaysApply: true" in claude_md
    assert "# Project Instructions" in claude_md


def test_init_fails_if_already_initialized(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "Already initialized" in result.output


def test_init_output_message(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert "Initialized" in result.output
    assert "agentpack.yaml" in result.output
    assert "CLAUDE.md" in result.output
    assert "agentpack generate" in result.output


def test_init_defaults_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".agentpack" / "agentpack.yaml").exists()


# ---------------------------------------------------------------------------
# Generate helpers
# ---------------------------------------------------------------------------


def _init_with_rules(tmp_path, agents="[claude, cursor]"):
    """Helper: init a repo and add sample rules/skills for generate tests."""
    runner.invoke(app, ["init", str(tmp_path)])
    (tmp_path / ".agentpack" / "agentpack.yaml").write_text(
        f"agents: {agents}\ngitignore: true\n"
    )
    (tmp_path / ".agentpack" / "rules" / "coding.md").write_text(
        "---\ndescription: Coding standards\n---\n\n# Coding\n"
    )
    skill_dir = tmp_path / ".agentpack" / "skills" / "deploy"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: deploy\ndescription: Deploy skill\n---\n\n# Deploy\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Generate — basic output
# ---------------------------------------------------------------------------


def test_generate_fails_without_agentpack(tmp_path):
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 1
    assert "Not initialized" in result.output


def test_generate_claude_agents_md(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "CLAUDE.md").exists()


def test_generate_claude_modular_rules(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".claude" / "rules" / "coding.md").exists()


def test_generate_claude_skills(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".claude" / "skills" / "deploy" / "SKILL.md").exists()


def test_generate_claude_agents_md_not_in_rules_dir(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert not (tmp_path / ".claude" / "rules" / "CLAUDE.md").exists()


def test_generate_cursor_agents_md_not_in_rules_dir(tmp_path):
    """CLAUDE.md must never be placed inside .cursor/rules/ regardless of agents config."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert not (tmp_path / ".cursor" / "rules" / "CLAUDE.md").exists()


def test_generate_cursor_modular_rules(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".cursor" / "rules" / "coding.md").exists()


def test_generate_cursor_no_skills_when_claude_configured(tmp_path):
    """When both agents are configured, cursor reads skills from .claude/skills/."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert not (tmp_path / ".cursor" / "skills").exists()


def test_generate_cursor_skills_when_cursor_only(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".cursor" / "skills" / "deploy" / "SKILL.md").exists()


def test_generate_claude_md_at_root_not_in_claude_dir(tmp_path):
    """CLAUDE.md must be at project root, not inside .claude/."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    assert not (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_generate_agents_md_at_root_cursor_only(tmp_path):
    """cursor-only config produces AGENTS.md at project root."""
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "AGENTS.md").exists()


def test_generate_no_agents_md_when_claude_present(tmp_path):
    """AGENTS.md is not generated when claude is in the agents list."""
    _init_with_rules(tmp_path)  # [claude, cursor]
    runner.invoke(app, ["generate", str(tmp_path)])
    assert not (tmp_path / "AGENTS.md").exists()


def test_generate_agents_md_has_html_marker(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / "AGENTS.md").read_text()
    assert content.startswith("<!-- GENERATED BY agentpack.")
    assert ".agentpack/rules/CLAUDE.md" in content


def test_generate_agents_md_strips_frontmatter(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / "AGENTS.md").read_text()
    assert "---" not in content
    assert "alwaysApply" not in content


def test_generate_agents_md_skips_user_defined(tmp_path):
    """User-defined AGENTS.md at project root is not overwritten."""
    _init_with_rules(tmp_path, agents="[cursor]")
    (tmp_path / "AGENTS.md").write_text("# My own AGENTS.md\n")
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert "WARN" in result.output
    assert "skipping" in result.output
    assert (tmp_path / "AGENTS.md").read_text() == "# My own AGENTS.md\n"


def test_generate_agents_md_force_overwrites_user_defined(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    (tmp_path / "AGENTS.md").write_text("# My own AGENTS.md\n")
    result = runner.invoke(app, ["generate", "--force", str(tmp_path)])
    assert "WARN" not in result.output
    assert "GENERATED BY agentpack" in (tmp_path / "AGENTS.md").read_text()


def test_generate_claude_md_skips_user_defined(tmp_path):
    """User-defined CLAUDE.md at project root is not overwritten."""
    _init_with_rules(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# My own CLAUDE.md\n")
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert "WARN" in result.output
    assert "skipping" in result.output
    assert (tmp_path / "CLAUDE.md").read_text() == "# My own CLAUDE.md\n"


def test_generate_gitignore_claude_md_entry(tmp_path):
    _init_with_rules(tmp_path, agents="[claude]")
    runner.invoke(app, ["generate", str(tmp_path)])
    gitignore = (tmp_path / ".gitignore").read_text()
    assert "CLAUDE.md" in gitignore


def test_generate_gitignore_agents_md_cursor_only(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    gitignore = (tmp_path / ".gitignore").read_text()
    assert "AGENTS.md" in gitignore
    assert "CLAUDE.md" not in gitignore


def test_generate_gitignore_no_agents_md_when_claude_present(tmp_path):
    """AGENTS.md must not appear in .gitignore when claude is also configured."""
    _init_with_rules(tmp_path)  # [claude, cursor]
    runner.invoke(app, ["generate", str(tmp_path)])
    gitignore = (tmp_path / ".gitignore").read_text()
    assert "AGENTS.md" not in gitignore


def test_generate_cleanup_removes_stale_claude_md(tmp_path):
    """Switching from [claude] to [cursor] removes the previously generated CLAUDE.md."""
    _init_with_rules(tmp_path, agents="[claude]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "CLAUDE.md").exists()

    (tmp_path / ".agentpack" / "agentpack.yaml").write_text("agents: [cursor]\ngitignore: true\n")
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "AGENTS.md").exists()


def test_generate_cleanup_removes_stale_agents_md(tmp_path):
    """Switching from [cursor] to [claude] removes the previously generated AGENTS.md."""
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "AGENTS.md").exists()

    (tmp_path / ".agentpack" / "agentpack.yaml").write_text("agents: [claude]\ngitignore: true\n")
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()


def test_generate_content_preserved(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / ".claude" / "rules" / "coding.md").read_text()
    assert "Coding standards" in content


def test_generate_gitignore_updated(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    gitignore = (tmp_path / ".gitignore").read_text()
    assert "CLAUDE.md" in gitignore
    assert ".claude/" in gitignore
    assert ".cursor/" in gitignore


def test_generate_gitignore_no_duplicates(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    runner.invoke(app, ["generate", str(tmp_path)])
    gitignore = (tmp_path / ".gitignore").read_text()
    assert gitignore.count("CLAUDE.md") == 1
    assert gitignore.count(".claude/") == 1


def test_generate_only_claude(tmp_path):
    _init_with_rules(tmp_path, agents="[claude]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".cursor").exists()


def test_generate_only_cursor(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".claude").exists()


def test_generate_defaults_to_cwd(tmp_path, monkeypatch):
    _init_with_rules(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["generate"])
    assert result.exit_code == 0
    assert (tmp_path / "CLAUDE.md").exists()


def test_generate_output_message(tmp_path):
    _init_with_rules(tmp_path)
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 0
    assert "Generating" in result.output
    assert "Done" in result.output


# ---------------------------------------------------------------------------
# Generated file markers
# ---------------------------------------------------------------------------


def test_generate_claude_md_has_html_marker(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / "CLAUDE.md").read_text()
    assert content.startswith("<!-- GENERATED BY agentpack.")
    assert ".agentpack/rules/CLAUDE.md" in content


def test_generate_claude_md_strips_frontmatter(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "---" not in content
    assert "alwaysApply" not in content


def test_generate_rules_have_yaml_marker(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / ".claude" / "rules" / "coding.md").read_text()
    assert content.startswith("---\n# GENERATED BY agentpack.")
    assert ".agentpack/rules/coding.md" in content


def test_generate_skills_have_yaml_marker(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / ".claude" / "skills" / "deploy" / "SKILL.md").read_text()
    assert "# GENERATED BY agentpack." in content
    assert ".agentpack/skills/deploy/SKILL.md" in content


def test_generate_cursor_rules_have_yaml_marker(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    content = (tmp_path / ".cursor" / "rules" / "coding.md").read_text()
    assert "# GENERATED BY agentpack." in content
    assert ".agentpack/rules/coding.md" in content


# ---------------------------------------------------------------------------
# Overwrite protection
# ---------------------------------------------------------------------------


def test_generate_skips_modified_file(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My custom rules\n")
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert "WARN" in result.output
    assert "skipping" in result.output
    assert target.read_text() == "# My custom rules\n"


def test_generate_force_overwrites_modified_file(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My custom rules\n")
    result = runner.invoke(app, ["generate", "--force", str(tmp_path)])
    assert "WARN" not in result.output
    assert "GENERATED BY agentpack" in target.read_text()


def test_generate_overwrites_marker_file(tmp_path):
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    result = runner.invoke(app, ["generate", str(tmp_path)])
    assert result.exit_code == 0
    assert "WARN" not in result.output


# ---------------------------------------------------------------------------
# Supplementary directories
# ---------------------------------------------------------------------------


def test_generate_copies_supplementary_dirs(tmp_path):
    _init_with_rules(tmp_path)
    scripts_dir = tmp_path / ".agentpack" / "skills" / "deploy" / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run.sh").write_text("#!/bin/bash\necho deploy")
    runner.invoke(app, ["generate", str(tmp_path)])
    out_script = tmp_path / ".claude" / "skills" / "deploy" / "scripts" / "run.sh"
    assert out_script.exists()
    assert "echo deploy" in out_script.read_text()


def test_generate_copies_supplementary_dirs_cursor_only(tmp_path):
    _init_with_rules(tmp_path, agents="[cursor]")
    refs_dir = tmp_path / ".agentpack" / "skills" / "deploy" / "references"
    refs_dir.mkdir()
    (refs_dir / "guide.md").write_text("# Guide")
    runner.invoke(app, ["generate", str(tmp_path)])
    out = tmp_path / ".cursor" / "skills" / "deploy" / "references" / "guide.md"
    assert out.exists()


# ---------------------------------------------------------------------------
# Cleanup of stale generated files
# ---------------------------------------------------------------------------


def test_generate_removes_stale_rule_on_rename(tmp_path):
    """Renaming a source rule removes the old generated file on next generate."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    old_rule = tmp_path / ".claude" / "rules" / "coding.md"
    assert old_rule.exists()

    (tmp_path / ".agentpack" / "rules" / "coding.md").rename(
        tmp_path / ".agentpack" / "rules" / "coding-renamed.md"
    )
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not old_rule.exists()
    assert (tmp_path / ".claude" / "rules" / "coding-renamed.md").exists()


def test_generate_removes_stale_cursor_rule_on_rename(tmp_path):
    """Renaming a source rule removes the old cursor-generated file on next generate."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    old_rule = tmp_path / ".cursor" / "rules" / "coding.md"
    assert old_rule.exists()

    (tmp_path / ".agentpack" / "rules" / "coding.md").rename(
        tmp_path / ".agentpack" / "rules" / "coding-renamed.md"
    )
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not old_rule.exists()
    assert (tmp_path / ".cursor" / "rules" / "coding-renamed.md").exists()


def test_generate_removes_stale_skill_on_rename(tmp_path):
    """Renaming a skill source removes the old generated SKILL.md on next generate."""
    _init_with_rules(tmp_path, agents="[cursor]")
    runner.invoke(app, ["generate", str(tmp_path)])
    old_skill = tmp_path / ".cursor" / "skills" / "deploy" / "SKILL.md"
    assert old_skill.exists()

    (tmp_path / ".agentpack" / "skills" / "deploy").rename(
        tmp_path / ".agentpack" / "skills" / "deploy-v2"
    )
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not old_skill.exists()
    assert (tmp_path / ".cursor" / "skills" / "deploy-v2" / "SKILL.md").exists()


def test_generate_cleanup_preserves_user_files(tmp_path):
    """Cleanup only removes marker files; user files without a marker are preserved."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    user_file = tmp_path / ".claude" / "rules" / "my-custom.md"
    user_file.write_text("# My Custom Rule\n")

    runner.invoke(app, ["generate", str(tmp_path)])

    assert user_file.exists()


def test_generate_cleanup_removes_deleted_source_rule(tmp_path):
    """Deleting a source rule removes its generated output on next generate."""
    _init_with_rules(tmp_path)
    runner.invoke(app, ["generate", str(tmp_path)])
    generated = tmp_path / ".claude" / "rules" / "coding.md"
    assert generated.exists()

    (tmp_path / ".agentpack" / "rules" / "coding.md").unlink()
    runner.invoke(app, ["generate", str(tmp_path)])

    assert not generated.exists()


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def test_generate_case_insensitive_skill_md(tmp_path):
    """_find_skill_md matches skill.md case-insensitively."""
    _init_with_rules(tmp_path)
    skill_dir = tmp_path / ".agentpack" / "skills" / "review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.md").write_text(
        "---\nname: review\ndescription: Review\n---\n\n# Review\n"
    )
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".claude" / "skills" / "review" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Sync — helpers
# ---------------------------------------------------------------------------


def _git(*args, cwd):
    """Run a git command, raising on failure."""
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


def _make_remote(tmp_path, name="remote", path=".agentpack", rules=None, skills=None):
    """Create a local git repo with .agentpack/ layout. Returns its path (usable as git URL)."""
    remote_dir = tmp_path / name
    remote_dir.mkdir()
    rules_dir = remote_dir / path / "rules"
    skills_dir = remote_dir / path / "skills"
    rules_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    for filename, content in (rules or {}).items():
        (rules_dir / filename).write_text(content)

    for skill_name, skill_content in (skills or {}).items():
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(skill_content)

    _git("init", cwd=remote_dir)
    _git("config", "user.email", "test@test.com", cwd=remote_dir)
    _git("config", "user.name", "Test", cwd=remote_dir)
    _git("add", ".", cwd=remote_dir)
    _git("commit", "-m", "init", cwd=remote_dir)
    return remote_dir


def _init_with_remotes(tmp_path, remotes_yaml="", monkeypatch=None):
    """Init a repo and write agentpack.yaml with given remotes config."""
    runner.invoke(app, ["init", str(tmp_path)])
    config = f"agents: [claude, cursor]\ngitignore: true\n{remotes_yaml}"
    (tmp_path / ".agentpack" / "agentpack.yaml").write_text(config)
    if monkeypatch:
        # Redirect ~/.cache to tmp dir so tests don't pollute real cache
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path


import shutil
import subprocess


# ---------------------------------------------------------------------------
# Sync — no remotes
# ---------------------------------------------------------------------------


def test_sync_no_remotes_prints_message(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "No remotes configured" in result.output


def test_sync_not_initialized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1
    assert "Not initialized" in result.output


# ---------------------------------------------------------------------------
# Sync — clone and pull
# ---------------------------------------------------------------------------


def test_sync_clones_remote_on_first_run(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: Shared\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    cache = tmp_path / "home" / ".cache" / "agentpack" / "remotes" / "myremote"
    assert (cache / ".git").exists()


def test_sync_pulls_on_second_run(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: v1\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])

    # Update remote
    rules_dir = remote / ".agentpack" / "rules"
    (rules_dir / "shared.md").write_text("---\ndescription: v2\n---\n")
    _git("add", ".", cwd=remote)
    _git("commit", "-m", "update", cwd=remote)

    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    synced = (tmp_path / ".agentpack" / "rules" / "shared.md").read_text()
    assert "v2" in synced


# ---------------------------------------------------------------------------
# Sync — rules
# ---------------------------------------------------------------------------


def test_sync_copies_rules_with_marker(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: Shared\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    content = (tmp_path / ".agentpack" / "rules" / "shared.md").read_text()
    assert "SYNCED BY agentpack. Remote: myremote" in content


def test_sync_skips_local_rule_without_marker(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"coding.md": "---\ndescription: Remote coding\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    # Place a local file with same name but no sync marker
    (tmp_path / ".agentpack" / "rules" / "coding.md").write_text("# My local rule\n")
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    assert (tmp_path / ".agentpack" / "rules" / "coding.md").read_text() == "# My local rule\n"


def test_sync_removes_stale_rule(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: Shared\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    assert (tmp_path / ".agentpack" / "rules" / "shared.md").exists()

    # Remove the rule from the remote
    (remote / ".agentpack" / "rules" / "shared.md").unlink()
    _git("add", ".", cwd=remote)
    _git("commit", "-m", "remove shared", cwd=remote)

    runner.invoke(app, ["sync"])
    assert not (tmp_path / ".agentpack" / "rules" / "shared.md").exists()


def test_sync_updates_changed_rule(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: v1\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])

    (remote / ".agentpack" / "rules" / "shared.md").write_text("---\ndescription: v2\n---\n")
    _git("add", ".", cwd=remote)
    _git("commit", "-m", "update shared", cwd=remote)

    runner.invoke(app, ["sync"])
    content = (tmp_path / ".agentpack" / "rules" / "shared.md").read_text()
    assert "v2" in content


# ---------------------------------------------------------------------------
# Sync — skills
# ---------------------------------------------------------------------------


def test_sync_copies_skill_with_marker(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path,
        skills={"review": "---\nname: review\ndescription: Review skill\n---\n"},
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    skill_md = tmp_path / ".agentpack" / "skills" / "review" / "SKILL.md"
    assert skill_md.exists()
    assert "SYNCED BY agentpack. Remote: myremote" in skill_md.read_text()


def test_sync_copies_skill_supplementary_dirs(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path,
        skills={"deploy": "---\nname: deploy\ndescription: Deploy\n---\n"},
    )
    # Add a supplementary directory in the remote skill
    scripts_dir = remote / ".agentpack" / "skills" / "deploy" / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run.sh").write_text("#!/bin/bash\necho deploy")
    _git("add", ".", cwd=remote)
    _git("commit", "-m", "add scripts", cwd=remote)

    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    out_script = tmp_path / ".agentpack" / "skills" / "deploy" / "scripts" / "run.sh"
    assert out_script.exists()
    assert "echo deploy" in out_script.read_text()


def test_sync_skips_local_skill_without_marker(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path,
        skills={"deploy": "---\nname: deploy\ndescription: Remote deploy\n---\n"},
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    # Place a local skill with no sync marker
    local_skill = tmp_path / ".agentpack" / "skills" / "deploy"
    local_skill.mkdir(parents=True)
    (local_skill / "SKILL.md").write_text("---\nname: deploy\ndescription: Local deploy\n---\n")

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    assert "Local deploy" in (local_skill / "SKILL.md").read_text()


def test_sync_removes_stale_skill(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path,
        skills={"review": "---\nname: review\ndescription: Review\n---\n"},
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    assert (tmp_path / ".agentpack" / "skills" / "review").exists()

    shutil.rmtree(remote / ".agentpack" / "skills" / "review")
    _git("add", ".", cwd=remote)
    _git("commit", "-m", "remove review", cwd=remote)

    runner.invoke(app, ["sync"])
    assert not (tmp_path / ".agentpack" / "skills" / "review").exists()


# ---------------------------------------------------------------------------
# Sync — config formats
# ---------------------------------------------------------------------------


def test_sync_bare_string_remote_config(tmp_path, monkeypatch):
    remote = _make_remote(tmp_path, rules={"shared.md": "---\ndescription: Shared\n---\n"})
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert (tmp_path / ".agentpack" / "rules" / "shared.md").exists()


def test_sync_object_remote_config_with_custom_path(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path, path="agent-rules", rules={"shared.md": "---\ndescription: Shared\n---\n"}
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote:\n    url: {remote}\n    path: agent-rules\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert (tmp_path / ".agentpack" / "rules" / "shared.md").exists()


# ---------------------------------------------------------------------------
# Sync — multi-remote priority
# ---------------------------------------------------------------------------


def test_sync_later_remote_overrides_earlier(tmp_path, monkeypatch):
    remote_a = _make_remote(
        tmp_path, name="remote_a", rules={"shared.md": "---\ndescription: From A\n---\n"}
    )
    remote_b = _make_remote(
        tmp_path, name="remote_b", rules={"shared.md": "---\ndescription: From B\n---\n"}
    )
    # remote_b is listed last → higher priority
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  remote_a: {remote_a}\n  remote_b: {remote_b}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    content = (tmp_path / ".agentpack" / "rules" / "shared.md").read_text()
    assert "From B" in content
    assert "Remote: remote_b" in content


# ---------------------------------------------------------------------------
# Sync — error handling
# ---------------------------------------------------------------------------


def test_sync_continues_on_unreachable_remote(tmp_path, monkeypatch):
    remote_good = _make_remote(
        tmp_path, name="remote_good", rules={"shared.md": "---\ndescription: Good\n---\n"}
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=(
            "remotes:\n"
            "  bad_remote: /nonexistent/path/to/repo\n"
            f"  good_remote: {remote_good}\n"
        ),
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync"])
    # Exits with error because one remote failed
    assert result.exit_code == 1
    # But the good remote was still synced
    assert (tmp_path / ".agentpack" / "rules" / "shared.md").exists()


# ---------------------------------------------------------------------------
# Sync + generate integration
# ---------------------------------------------------------------------------


def test_generate_incorporates_synced_rules(tmp_path, monkeypatch):
    remote = _make_remote(
        tmp_path, rules={"security.md": "---\ndescription: Security rules\n---\n\n# Security\n"}
    )
    _init_with_remotes(
        tmp_path,
        remotes_yaml=f"remotes:\n  myremote: {remote}\n",
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["sync"])
    runner.invoke(app, ["generate", str(tmp_path)])
    assert (tmp_path / ".claude" / "rules" / "security.md").exists()
    content = (tmp_path / ".claude" / "rules" / "security.md").read_text()
    assert "GENERATED BY agentpack" in content
    assert "Security rules" in content
