"""
(Incomplete) test suite for repo_checks.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from fastcore.net import HTTP4xxClientError

from edx_repo_tools.repo_checks import repo_checks


@pytest.fixture
def maintenance_label():
    """
    Quickly make a basic label to return via the API.
    """
    label = MagicMock()
    label.name = "maintenance"
    label.color = "ff9125"
    label.description = (
        "Routine upkeep necessary for the health of the platform"
    )

    return label


# Our list of expected labels, normally defined in labels.yaml.
labels_yaml = [
    {
        "name": "maintenance",
        "color": "ff9125",
        "description": "Routine upkeep necessary for the health of the platform",
    }
]


@patch.object(repo_checks.Labels, "labels", labels_yaml)
class TestLabelsCheck:
    def test_check_for_no_change(self, maintenance_label):
        api = MagicMock()
        api.issues.list_labels_for_repo.side_effect = [[maintenance_label], None]
        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        # Make sure that the check returns True, indicating that no changes need to be made.
        assert check_cls.check()[0]

    def test_addition(self, maintenance_label):
        api = MagicMock()
        api.issues.list_labels_for_repo.return_value = []
        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        # The check should be false because the maintenance label should be missing.
        assert check_cls.check()[0] == False

        check_cls.fix()
        assert api.issues.create_label.called

        call_args = api.issues.create_label.call_args
        expected_call = call(
            owner="test_org",
            repo="test_repo",
            name=maintenance_label.name,
            color=maintenance_label.color,
            description=maintenance_label.description,
        )
        assert call_args == expected_call
        assert not api.issues.update_label.called

    def test_update_label(self, maintenance_label):
        maintenance_label.name = ":+1: Ma.in-t 'e'n_a\"nce!\" :-1:"
        api = MagicMock()
        api.issues.list_labels_for_repo.side_effect = [[maintenance_label], None]

        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        assert check_cls.check()[0] == False
        check_cls.fix()

        call_args = api.issues.update_label.call_args
        expected_call = call(
            owner="test_org",
            repo="test_repo",
            name=maintenance_label.name,
            color=maintenance_label.color,
            new_name="maintenance",
            description=maintenance_label.description,
        )

        assert call_args == expected_call
        assert not api.issues.create_label.called
        assert api.issues.update_label.called


def make_workflow(name, state, workflow_id=1):
    """
    Quickly make a basic workflow object to return via the API.
    """
    w = MagicMock()
    w.name = name
    w.state = state
    w.id = workflow_id
    return w


def make_workflows_api(workflows):
    """
    Make a mock API that returns the given workflows from list_repo_workflows.
    """
    api = MagicMock()
    response = MagicMock()
    response.workflows = workflows
    response.total_count = len(workflows)
    api.actions.list_repo_workflows.return_value = response
    return api


class TestEnsureWorkflowsEnabled:
    def test_check_all_active(self):
        api = make_workflows_api([make_workflow("CI", "active"), make_workflow("Lint", "active")])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        # Make sure that the check returns True when all workflows are active.
        assert check_cls.check()[0] == True

    def test_check_disabled_inactivity(self):
        api = make_workflows_api([make_workflow("CI", "active"), make_workflow("Upgrade", "disabled_inactivity", 42)])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        # The check should be false because a workflow is disabled due to inactivity.
        assert check_cls.check()[0] == False

    def test_check_disabled_fork(self):
        api = make_workflows_api([make_workflow("Upgrade", "disabled_fork", 99)])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        # The check should be false because a workflow is disabled due to fork status.
        assert check_cls.check()[0] == False

    def test_check_disabled_manually_ignored(self):
        api = make_workflows_api([make_workflow("CI", "active"), make_workflow("Secret", "disabled_manually")])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        # Manually disabled workflows should not be flagged.
        assert check_cls.check()[0] == True

    def test_fix_enables_disabled_workflows(self):
        api = make_workflows_api([make_workflow("Upgrade", "disabled_inactivity", 42)])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        check_cls.check()
        steps = check_cls.fix()
        # fix() should call enable_workflow with the correct arguments.
        assert api.actions.enable_workflow.call_args == call(
            owner="test_org",
            repo="test_repo",
            workflow_id=42,
        )
        assert len(steps) == 1
        assert "Upgrade" in steps[0]

    def test_dry_run_does_not_call_enable(self):
        api = make_workflows_api([make_workflow("Upgrade", "disabled_inactivity", 42)])
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        check_cls.check()
        check_cls.dry_run()
        # dry_run() should not make any changes to GitHub.
        assert not api.actions.enable_workflow.called

    def test_is_relevant_false_for_security_fork(self):
        api = MagicMock()
        api.repos.get.return_value = MagicMock(private=True, default_branch="main")
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo-ghsa-1234-5678-9012")
        assert check_cls.is_relevant() == False

    @patch("edx_repo_tools.repo_checks.repo_checks.is_empty", return_value=True)
    def test_is_relevant_false_for_empty_repo(self, _):
        api = MagicMock()
        api.repos.get.return_value = MagicMock(private=False, default_branch="main")
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        assert check_cls.is_relevant() == False

    def test_is_relevant_true_for_normal_repo(self):
        api = MagicMock()
        api.repos.get.return_value = MagicMock(private=False, default_branch="main")
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        assert check_cls.is_relevant() == True

    def test_fix_continues_on_api_error(self):
        api = make_workflows_api([
            make_workflow("Failing", "disabled_inactivity", 1),
            make_workflow("Upgrade", "disabled_inactivity", 2),
        ])
        api.actions.enable_workflow.side_effect = [
            HTTP4xxClientError("url", 422, "Unprocessable Entity", {}, None),
            None,
        ]
        check_cls = repo_checks.EnsureWorkflowsEnabled(api, "test_org", "test_repo")
        check_cls.check()
        steps = check_cls.fix()
        # fix() should attempt all workflows even if one fails.
        assert api.actions.enable_workflow.call_count == 2
        assert any("Failed" in s for s in steps)
        assert any("Upgrade" in s for s in steps)
