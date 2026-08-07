"""UTILS-2 — subprocess env secret-scrub (port of utils/subprocessEnv.ts).

Anti-exfiltration: by default (secure-by-default), secret env vars (+ their
INPUT_ GitHub-Action twins) are stripped from a child process's environment so
a prompt-injected Bash command can't read them via ${VAR}. The scrubbing can be
disabled by setting CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS to a truthy value
(opt-out for local development). Wired at the bash (fg+bg) + hook subprocess sites.
"""
from __future__ import annotations

import os

import pytest

from src.utils.subprocess_env import subprocess_env


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS",
              "ANTHROPIC_API_KEY", "INPUT_ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", 
              "SSH_SIGNING_KEY"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_default_scrubs_secrets(monkeypatch):
    """By default (secure-by-default), secrets are scrubbed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sekret")
    e = subprocess_env()
    assert "ANTHROPIC_API_KEY" not in e  # scrubbed by default
    assert "PATH" in e  # non-secret retained


def test_allow_secrets_flag_passes_through(monkeypatch):
    """CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS=1 opts out of scrubbing."""
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sekret")
    e = subprocess_env()
    assert e["ANTHROPIC_API_KEY"] == "sekret"  # passed through when opt-out flag set


def test_explicit_scrub_flag_still_works(monkeypatch):
    """CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1 explicitly enables scrubbing (backwards compat)."""
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "s")
    monkeypatch.setenv("INPUT_ANTHROPIC_API_KEY", "twin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "a")
    monkeypatch.setenv("SSH_SIGNING_KEY", "k")
    e = subprocess_env()
    for gone in ("ANTHROPIC_API_KEY", "INPUT_ANTHROPIC_API_KEY",
                 "AWS_SECRET_ACCESS_KEY", "SSH_SIGNING_KEY"):
        assert gone not in e
    assert "PATH" in e  # non-secret retained


def test_explicit_scrub_overrides_allow_secrets(monkeypatch):
    """CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1 takes precedence over ALLOW_SECRETS."""
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "1")
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "s")
    e = subprocess_env()
    assert "ANTHROPIC_API_KEY" not in e  # explicit scrub wins


def test_scrub_flag_truthy_variants(monkeypatch):
    """Test truthy value recognition for CLAUDE_CODE_SUBPROCESS_ENV_SCRUB."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "s")
    # Note: With secure-by-default, we need ALLOW_SECRETS to test the scrub flag variants
    for v, scrubbed in [("true", True), ("yes", True), ("on", True),
                        ("0", False), ("false", False), ("", False)]:
        # Set ALLOW_SECRETS=1 first to disable default scrubbing
        monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS", "1")
        monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", v)
        # When SCRUB is truthy, it should override ALLOW_SECRETS
        assert ("ANTHROPIC_API_KEY" not in subprocess_env()) is scrubbed


def test_allow_secrets_truthy_variants(monkeypatch):
    """Test truthy value recognition for CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "s")
    for v, allowed in [("true", True), ("yes", True), ("on", True), ("1", True),
                       ("0", False), ("false", False), ("", False)]:
        monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_ALLOW_SECRETS", v)
        # When ALLOW_SECRETS is truthy, secrets should pass through
        assert ("ANTHROPIC_API_KEY" in subprocess_env()) is allowed


def test_returns_fresh_dict_not_os_environ(monkeypatch):
    e = subprocess_env()
    e["_MUT"] = "x"
    assert "_MUT" not in os.environ


def test_explicit_base(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "1")
    e = subprocess_env({"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1", "ANTHROPIC_API_KEY": "x", "KEEP": "y"})
    assert "ANTHROPIC_API_KEY" not in e and e["KEEP"] == "y"


def test_all_23_scrub_vars_stripped(monkeypatch):
    from src.utils.subprocess_env import _GHA_SUBPROCESS_SCRUB
    assert len(_GHA_SUBPROCESS_SCRUB) == 23
    monkeypatch.setenv("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "1")
    for v in _GHA_SUBPROCESS_SCRUB:
        monkeypatch.setenv(v, "secret")
        monkeypatch.setenv(f"INPUT_{v}", "twin")
    e = subprocess_env()
    for v in _GHA_SUBPROCESS_SCRUB:
        assert v not in e and f"INPUT_{v}" not in e, v
    # the flag itself is preserved for the child (TS keeps it)
    assert e.get("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB") == "1"
