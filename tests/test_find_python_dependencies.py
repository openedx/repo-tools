from unittest.mock import patch

from edx_repo_tools.find_dependencies.find_python_dependencies import (
    iter_requirement_names,
    main,
)


def test_iter_requirement_names_requirements_txt(tmp_path):
    req_file = tmp_path / "base.txt"
    req_file.write_text(
        "Django==4.2.1\n"
        "git+https://github.com/mitodl/edx-sga.git@abc123#egg=edx-sga\n"
    )
    assert sorted(iter_requirement_names(req_file)) == ["Django", "edx-sga"]


def test_iter_requirement_names_pyproject_toml(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
        [project]
        name = "sample"
        version = "0.1"
        dependencies = [
            "lxml[html_clean]",
            "edx-sga @ git+https://github.com/mitodl/edx-sga.git@abc123",
        ]

        [project.optional-dependencies]
        extra = ["requests"]

        [dependency-groups]
        test-base = ["pytest"]
        test = [{include-group = "test-base"}, "responses"]
        """
    )
    names = set(iter_requirement_names(pyproject))
    assert names == {"lxml", "edx-sga", "requests", "pytest", "responses"}


def test_iter_requirement_names_uv_lock(tmp_path):
    uv_lock = tmp_path / "uv.lock"
    uv_lock.write_text(
        """
        version = 1

        [[package]]
        name = "lxml"
        version = "5.3.2"

        [[package]]
        name = "edx-sga"
        version = "0.1"
        """
    )
    assert sorted(iter_requirement_names(uv_lock)) == ["edx-sga", "lxml"]


def test_main_flags_second_party_dependency_from_uv_lock(tmp_path):
    uv_lock = tmp_path / "uv.lock"
    uv_lock.write_text(
        """
        version = 1

        [[package]]
        name = "edx-sga"
        version = "0.1"

        [[package]]
        name = "django"
        version = "4.2.1"
        """
    )

    def fake_request_package_info_url(package):
        return {
            "edx-sga": "https://github.com/mitodl/edx-sga",
            "django": "https://github.com/django/django",
        }.get(package)

    with patch(
        "edx_repo_tools.find_dependencies.find_python_dependencies.request_package_info_url",
        side_effect=fake_request_package_info_url,
    ):
        with patch(
            "edx_repo_tools.find_dependencies.find_python_dependencies.exit"
        ) as mock_exit:
            main.callback(directories=[str(uv_lock)], ignore_paths=[])
            mock_exit.assert_called_once_with(1)


def test_main_respects_ignore_list_with_pyproject_toml(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
        [project]
        name = "sample"
        version = "0.1"
        dependencies = ["edx-sga"]
        """
    )

    with patch(
        "edx_repo_tools.find_dependencies.find_python_dependencies.request_package_info_url",
        return_value="https://github.com/mitodl/edx-sga",
    ):
        with patch(
            "edx_repo_tools.find_dependencies.find_python_dependencies.exit"
        ) as mock_exit:
            main.callback(
                directories=[str(pyproject)],
                ignore_paths=["https://github.com/mitodl/edx-sga"],
            )
            mock_exit.assert_not_called()
