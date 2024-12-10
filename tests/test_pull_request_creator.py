# pylint: disable=missing-module-docstring,missing-class-docstring

from os import path
from unittest import TestCase
from unittest.mock import MagicMock, Mock, mock_open, patch

from edx_repo_tools.pull_request_creator import GitHubHelper, PullRequestCreator


class HelpersTestCase(TestCase):

    def test_close_existing_pull_requests(self):
        """
        Make sure we close only PR's by the correct author.
        """

        incorrect_pr_one = Mock()
        incorrect_pr_one.user.name = "Not John"
        incorrect_pr_one.user.login = "notJohn"
        incorrect_pr_one.number = 1
        incorrect_pr_one.head.ref = "incorrect-branch-name"
        incorrect_pr_one.base.ref = "master"

        incorrect_pr_two = Mock()
        incorrect_pr_two.user.name = "John Smith"
        incorrect_pr_two.user.login = "johnsmithiscool100"
        incorrect_pr_two.number = 2
        incorrect_pr_two.head.ref = "incorrect-branch-name-2"
        incorrect_pr_two.base.ref = "master"

        incorrect_pr_three = Mock()
        incorrect_pr_three.user.name = "John Smith"
        incorrect_pr_three.user.login = "fakeuser100"
        incorrect_pr_three.number = 5
        incorrect_pr_three.head.ref = "jenkins/upgrade-python-requirements-ce0515e"
        incorrect_pr_three.base.ref = "some-other-branch"

        correct_pr_one = Mock()
        correct_pr_one.user.name = "John Smith"
        correct_pr_one.user.login = "fakeuser100"
        correct_pr_one.number = 3
        correct_pr_one.head.ref = "repo-tools/upgrade-python-requirements-ce0515e"
        correct_pr_one.base.ref = "master"

        correct_pr_two = Mock()
        correct_pr_two.user.name = "John Smith"
        correct_pr_two.user.login = "fakeuser100"
        correct_pr_two.number = 4
        correct_pr_two.head.ref = "repo-tools/upgrade-python-requirements-0c51f37"
        correct_pr_two.base.ref = "master"

        mock_repo = Mock()
        mock_repo.get_pulls = MagicMock(return_value=[
            incorrect_pr_one,
            incorrect_pr_two,
            incorrect_pr_three,
            correct_pr_one,
            correct_pr_two
        ])

        deleted_pulls = GitHubHelper().close_existing_pull_requests(mock_repo, "fakeuser100", "John Smith")
        assert deleted_pulls == [3, 4]
        assert not incorrect_pr_one.edit.called
        assert not incorrect_pr_two.edit.called
        assert not incorrect_pr_three.edit.called
        assert correct_pr_one.edit.called
        assert correct_pr_two.edit.called

    def test_get_updated_files_list_no_change(self):
        git_instance = Mock()
        git_instance.ls_files = MagicMock(return_value="")
        with patch('edx_repo_tools.pull_request_creator.Git', return_value=git_instance):
            result = GitHubHelper().get_updated_files_list("edx-platform")
            assert result == []

    def test_get_updated_files_list_with_changes(self):
        git_instance = Mock()
        git_instance.ls_files = MagicMock(return_value="file1\nfile2")
        with patch('edx_repo_tools.pull_request_creator.Git', return_value=git_instance):
            result = GitHubHelper().get_updated_files_list("edx-platform")
            assert result == ["file1", "file2"]

    def test_update_list_of_files_no_change(self):
        repo_mock = Mock()
        repo_root = "../../edx-platform"
        file_path_list = []
        commit_message = "commit"
        sha = "abc123"
        username = "fakeusername100"

        return_sha = GitHubHelper().update_list_of_files(repo_mock, repo_root, file_path_list, commit_message, sha,
                                                         username)
        assert return_sha is None
        assert not repo_mock.create_git_tree.called
        assert not repo_mock.create_git_commit.called

    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.get_file_contents',
           return_value=None)
    @patch('edx_repo_tools.pull_request_creator.InputGitAuthor',
           return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.InputGitTreeElement',
           return_value=Mock())
    # pylint: disable=unused-argument
    def test_update_list_of_files_with_changes(self, get_file_contents_mock, author_mock, git_tree_mock):
        repo_mock = Mock()
        repo_root = "../../edx-platform"
        file_path_list = ["path/to/file1", "path/to/file2"]
        commit_message = "commit"
        sha = "abc123"
        username = "fakeusername100"

        return_sha = GitHubHelper().update_list_of_files(repo_mock, repo_root, file_path_list, commit_message, sha,
                                                         username)
        assert repo_mock.create_git_tree.called
        assert repo_mock.create_git_commit.called
        assert return_sha is not None
    # pylint: enable=unused-argument

    def test_get_file_contents(self):
        with patch("builtins.open", mock_open(read_data="data")) as mock_file:
            contents = GitHubHelper().get_file_contents("../../edx-platform", "path/to/file")
            mock_file.assert_called_with("../../edx-platform/path/to/file", "r", encoding='utf-8')
            assert contents == "data"


class UpgradePythonRequirementsPullRequestTestCase(TestCase):
    """
    Test Case class for PR creator.
    """

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.delete_branch', return_value=None)
    def test_no_changes(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                        update_files_mock, branch_exists_mock, current_commit_mock,
                        modified_list_mock, repo_mock, authenticate_mock,
                        close_existing_prs_mock):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR')
        pull_request_creator.create(True)

        assert authenticate_mock.called
        assert repo_mock.called
        assert modified_list_mock.called
        assert not branch_exists_mock.called
        assert not create_branch_mock.called
        assert not update_files_mock.called
        assert not create_pr_mock.called

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance',
           return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=False)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.delete_branch', return_value=None)
    def test_changes(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                     update_files_mock, branch_exists_mock, current_commit_mock,
                     modified_list_mock, repo_mock, authenticate_mock,
                     close_existing_prs_mock):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR')
        pull_request_creator.create(True)

        assert branch_exists_mock.called
        assert create_branch_mock.called
        self.assertEqual(create_branch_mock.call_count, 1)
        assert update_files_mock.called
        self.assertEqual(update_files_mock.call_count, 1)
        assert create_pr_mock.called

        create_pr_mock.title = "Python Requirements Update"
        create_pr_mock.diff_url = "/"
        create_pr_mock.repository.name = 'repo-health-data'

        basepath = path.dirname(__file__)

        filepath = path.abspath(path.join(basepath, "pull_request_creator_test_data", "diff.txt"))
        with open(filepath, "r") as f:
            content = f.read().encode('utf-8')
            with patch('requests.get') as mock_request:
                mock_request.return_value.content = content
                mock_request.return_value.status_code = 200
                GitHubHelper().verify_upgrade_packages(create_pr_mock)
            assert create_pr_mock.create_issue_comment.called
            assert not delete_branch_mock.called

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance',
           return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    # all above this unused params, no need to interact with those mocks
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=False)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('builtins.print')
    def test_outputs_url_on_success(self, print_mock, create_branch_mock, create_pr_mock,
                                    update_files_mock, branch_exists_mock, *args):
        """
        Ensure that a successful run outputs the URL consumable by github actions
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR', output_pr_url_for_github_action=True)
        pull_request_creator.create(False)

        assert branch_exists_mock.called
        assert create_branch_mock.called
        self.assertEqual(create_branch_mock.call_count, 1)
        assert update_files_mock.called
        self.assertEqual(update_files_mock.call_count, 1)
        assert create_pr_mock.called
        assert print_mock.call_count == 1
        found_matching_call = False
        for call in print_mock.call_args_list:
            if '$GITHUB_OUTPUT' in call.args[0]:
                found_matching_call = True
        assert found_matching_call

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=True)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.delete_branch', return_value=None)
    def test_branch_exists(self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
                           update_files_mock, branch_exists_mock, current_commit_mock,
                           modified_list_mock, repo_mock, authenticate_mock,
                           close_existing_prs_mock):
        """
        Ensure if a branch exists and delete_old_pull_requests is set to False, then there are no updates.
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR')
        pull_request_creator.create(False)

        assert branch_exists_mock.called
        assert not create_branch_mock.called
        assert not create_pr_mock.called
        assert not delete_branch_mock.called

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance',
           return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    # all above this unused params, no need to interact with those mocks
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=True)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.delete_branch', return_value=None)
    @patch('builtins.print')
    def test_branch_deletion(self, create_branch_mock, create_pr_mock,
                             update_files_mock, branch_exists_mock, delete_branch_mock, *args):
        """
        Ensure if a branch exists and delete_old_pull_requests is set, then branch is deleted
        before creating new PR.
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR', output_pr_url_for_github_action=True)
        pull_request_creator.create(True)

        assert branch_exists_mock.called
        assert delete_branch_mock.called
        assert create_branch_mock.called
        assert update_files_mock.called
        assert create_pr_mock.called

    def test_compare_upgrade_difference_with_major_changes(self):
        basepath = path.dirname(__file__)
        filepath = path.abspath(path.join(basepath, "pull_request_creator_test_data", "diff.txt"))
        with open(filepath, "r") as f:
            valid, suspicious = GitHubHelper().compare_pr_differnce(f.read())
            assert sorted(
                ['certifi', 'chardet', 'filelock', 'pip-tools', 'platformdirs', 'pylint', 'virtualenv']
            ) == [g['name'] for g in valid]

            assert sorted(
                ['cachetools', 'six', 'tox', 'pyproject-api', 'colorama', 'py', 'chardet', 'pyparsing', 'packaging']
            ) == [g['name'] for g in suspicious]

    def test_compare_upgrade_difference_with_minor_changes(self):
        basepath = path.dirname(__file__)
        filepath = path.abspath(path.join(basepath, "pull_request_creator_test_data", "minor_diff.txt"))
        with open(filepath, "r") as f:
            valid, suspicious = GitHubHelper().compare_pr_differnce(f.read())
            assert sorted(
                ['packaging']
            ) == [g['name'] for g in valid]

            assert sorted(
                []
            ) == [g['name'] for g in suspicious]

    def test_check_automerge_variable_value(self):
        with patch('requests.get') as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {
                'name': 'ENABLE_AUTOMERGE_FOR_DEPENDENCIES_PRS', 'value': 'True',
                'created_at': '2023-03-17T12:58:50Z', 'updated_at': '2023-03-17T13:01:12Z'
            }
            self.assertTrue(
                GitHubHelper().check_automerge_variable_value(
                    'https://foo/bar/testrepo/pulls/1'
                )
            )

            # in case of false value of variable.
            mock_request.return_value.json.return_value = {
                'name': 'ENABLE_AUTOMERGE_FOR_DEPENDENCIES_PRS', 'value': 'False',
                'created_at': '2023-03-17T12:58:50Z', 'updated_at': '2023-03-17T13:01:12Z'
            }
            self.assertFalse(
                GitHubHelper().check_automerge_variable_value(
                    'https://foo/bar/testrepo/pulls/1'
                )
            )
            # in case of no variable exists.
            mock_request.return_value.status_code = 404
            mock_request.return_value.json.return_value = {
                'name': 'ENABLE_AUTOMERGE_FOR_DEPENDENCIES_PRS', 'value': 'False',
                'created_at': '2023-03-17T12:58:50Z', 'updated_at': '2023-03-17T13:01:12Z'
            }
            self.assertFalse(
                GitHubHelper().check_automerge_variable_value(
                    'https://foo/bar/testrepo/pulls/1'
                )
            )

    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.close_existing_pull_requests',
           return_value=[])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_github_instance',
           return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.repo_from_remote', return_value=Mock())
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_updated_files_list',
           return_value=["requirements/edx/base.txt", "requirements/edx/coverage.txt"])
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.get_current_commit', return_value='1234567')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.branch_exists', return_value=False)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.update_list_of_files', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_pull_request')
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator.github_helper.create_branch', return_value=None)
    @patch('edx_repo_tools.pull_request_creator.PullRequestCreator._get_user',
           return_value=Mock(name="fake name", login="fake login"))
    @patch('edx_repo_tools.pull_request_creator.GitHubHelper.delete_branch', return_value=None)
    def test_changes_with_minor_versions_and_variable(
        self, delete_branch_mock, get_user_mock, create_branch_mock, create_pr_mock,
        update_files_mock, branch_exists_mock, current_commit_mock,
        modified_list_mock, repo_mock, authenticate_mock,
        close_existing_prs_mock
    ):
        """
        Ensure a merge with no changes to db files will not result in any updates.
        """
        pull_request_creator = PullRequestCreator('--repo_root=../../edx-platform', 'upgrade-branch', [],
                                                  [], 'Upgrade python requirements', 'Update python requirements',
                                                  'make upgrade PR')
        pull_request_creator.create(True)

        assert branch_exists_mock.called
        assert create_branch_mock.called
        self.assertEqual(create_branch_mock.call_count, 1)
        assert update_files_mock.called
        self.assertEqual(update_files_mock.call_count, 1)
        assert create_pr_mock.called

        create_pr_mock.title = "chore: Upgrade Python requirements"
        create_pr_mock.diff_url = "/"
        create_pr_mock.repository.name = 'xblock-lti-consumer'

        basepath = path.dirname(__file__)

        filepath = path.abspath(path.join(basepath, "pull_request_creator_test_data", "minor_diff.txt"))
        with open(filepath, "r") as f:
            content = f.read().encode('utf-8')
            with patch('requests.get') as mock_request:
                mock_request.return_value.content = content
                mock_request.return_value.status_code = 200

                # in case of `check_automerge_variable_value` false value label will not added.
                with patch(
                        'edx_repo_tools.pull_request_creator.GitHubHelper.check_automerge_variable_value'
                ) as check_automerge_variable_value:
                    check_automerge_variable_value.return_value = False
                    GitHubHelper().verify_upgrade_packages(create_pr_mock)
                    assert not create_pr_mock.set_labels.called
