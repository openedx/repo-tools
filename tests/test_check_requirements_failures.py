"""
Tests for check_requirements_failures.get_last_requirements_pr.
"""
from unittest import mock

from edx_repo_tools.check_requirements_failures import check_requirements_failures as crf

MODULE = "edx_repo_tools.check_requirements_failures.check_requirements_failures"
MERGED_PR = [{"number": 12, "title": "chore: Upgrade Python requirements",
              "mergedAt": "2026-09-20T10:00:00Z", "url": "https://github.com/o/r/pull/12"}]


def _fake_gh(default_branch):
    calls = []

    def fake(command):
        calls.append(command)
        if command[:2] == ["repo", "view"]:
            return {"defaultBranchRef": {"name": default_branch}} if default_branch else None
        return MERGED_PR

    return fake, calls


def test_requirements_pr_is_limited_to_the_default_branch():
    fake, calls = _fake_gh("master")
    with mock.patch(f"{MODULE}.run_gh_command", side_effect=fake):
        result = crf.get_last_requirements_pr("o", "r")

    pr_list = calls[-1]
    assert pr_list[:2] == ["pr", "list"]
    assert pr_list[pr_list.index("--base") + 1] == "master"
    assert result == {"date": "2026-09-20", "pr_number": 12, "url": "https://github.com/o/r/pull/12"}


def test_unknown_default_branch_falls_back_to_any_base():
    fake, calls = _fake_gh(None)
    with mock.patch(f"{MODULE}.run_gh_command", side_effect=fake):
        crf.get_last_requirements_pr("o", "r")

    assert "--base" not in calls[-1]


def test_get_default_branch_reads_the_name():
    with mock.patch(f"{MODULE}.run_gh_command", return_value={"defaultBranchRef": {"name": "main"}}):
        assert crf.get_default_branch("o", "r") == "main"
    with mock.patch(f"{MODULE}.run_gh_command", return_value=None):
        assert crf.get_default_branch("o", "r") is None
