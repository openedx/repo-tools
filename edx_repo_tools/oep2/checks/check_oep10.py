import ast
import logging

from path import Path
import tox.config
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet, Specifier
from packaging.version import Version
import six

LIBRARY_REQUIRED_DJANGO_VERSIONS = {'1.8', '1.11'}
APPLICATION_ALLOWED_DJANGO_VERSIONS = {
    SpecifierSet('>=1.8,<1.9'),
    SpecifierSet('>=1.11,<2.0'),
}

DJANGO_VERSIONS = {
    Version(f'{major}.{minor}.{patch}')
    for major, minors in {
        1: {
            8: range(19),
            9: range(14),
            10: range(8),
            11: range(1)
        }
    }.items()
    for minor, patches in minors.items()
    for patch in patches
}

LOG = logging.getLogger(__name__)


def setup_call(parsed_setup_py):
    for statement in parsed_setup_py.body:
        if not isinstance(statement, ast.Expr):
            continue

        expr = statement.value
        if not isinstance(expr, ast.Call):
            continue

        if not isinstance(expr.func, ast.Name):
            continue

        if expr.func.id != 'setup':
            continue

        return expr

    return None


def uses_pbr(parsed_setup_py):
    setup = setup_call(parsed_setup_py)

    if setup is None:
        return False

    for keyword in setup.keywords:
        if keyword.arg == 'pbr' and keyword.value:
            return True

    return False


def parsed_requirements_txt(requirements_txt):
    if not requirements_txt.exists():
        print("not exists")
        return

    for line in requirements_txt.lines():
        if line.strip().startswith('-r'):
            sub_requirements = requirements_txt.parent / line.replace('-r', '').strip()
            yield from parsed_requirements_txt(sub_requirements)
        else:
            try:
                yield Requirement(line)
            except InvalidRequirement:
                LOG.warning('Unable to parse requirement %r in %s', line, requirements_txt)


def requirement_is_django(req):
    try:
        if isinstance(req, str):
            req = Requirement(req)
        return req.name.lower() == 'django'
    except InvalidRequirement:
        return False


def requirements_txt_has_django(requirements_txt):
    for req in parsed_requirements_txt(requirements_txt):
        if requirement_is_django(req):
            return True
    return False


def setup_py_has_django(parsed_setup_py):
    setup = setup_call(parsed_setup_py)

    for keyword in setup.keywords:
        if keyword.arg == 'install_requires':
            for elt in keyword.value.elts:
                if not isinstance(elt, ast.Str):
                    continue
                if requirement_is_django(elt.s):
                    return True

    return False


def tox_tested_django_versions(tox_ini):
    tox_config = tox.config.parseconfig(['-c', str(tox_ini.abspath())])
    tested_versions = set()

    for env, config in tox_config.envconfigs.items():
        for dep in config.deps:
            if requirement_is_django(dep.name):
                req = Requirement(dep.name)
                tested_versions |= {
                    version
                    for version in ['1.8', '1.9', '1.10', '1.11', '2.0']
                    if version in req.specifier
                }
    return tested_versions


class OEP10:
    def check_django_versions(self, git_repo):
        """
        A repo is either a library or an application.

        If it's a library, then it should have a setup.py or a setup.cfg, and it should have a
        tox.ini file that runs its tests with at least django 1.8 and django 1.11, if
        its setup.py lists Django as a dependency.

        If it's a repository, then it should have a requirements/base.txt
        (or at least a requirements.txt) and that should pin
        either Django==1.8 or Django==1.11, if it specifies Django as a dependency.
        """
        working_dir = Path(git_repo.working_tree_dir)

        setup_py = working_dir / 'setup.py'
        setup_cfg = working_dir / 'setup.cfg'
        requirements_base_txt = working_dir / 'requirements/base.txt'
        requirements_txt = working_dir / 'requirements.txt'
        manage_py = working_dir / 'manage.py'
        tox_ini = working_dir / 'tox.ini'

        is_django_application = manage_py.exists()

        print(is_django_application)
        print(setup_py.exists())

        if requirements_base_txt.exists():
            requirements_file = requirements_base_txt
        else:
            requirements_file = requirements_txt

        print(requirements_file.exists())

        if not is_django_application and setup_py.exists():
            parsed_setup_py = ast.parse(setup_py.bytes(), 'setup.py')

            if uses_pbr(parsed_setup_py):
                has_django = requirements_txt_has_django(requirements_file)
            else:
                has_django = setup_py_has_django(parsed_setup_py)

            if not has_django:
                return

            tested_versions = tox_tested_django_versions(tox_ini)
            assert LIBRARY_REQUIRED_DJANGO_VERSIONS in tested_versions

        elif requirements_file.exists():
            django_specifier = None

            for req in parsed_requirements_txt(requirements_file):
                if requirement_is_django(req):
                    if django_specifier is None:
                        django_specifier = req.specifier
                    else:
                        django_specifier &= req.specifier

            if django_specifier is None:
                return

            largest_accepted_version = max(
                version
                for version in DJANGO_VERSIONS
                if version in django_specifier
            )

            for supported_version in APPLICATION_ALLOWED_DJANGO_VERSIONS:
                if largest_accepted_version in supported_version:
                    return
            msg = (
                "No allowed version range contained the largest allowed django " +
                f"version {largest_accepted_version} in the version specifier {django_specifier}"
            )
            assert False, msg
        else:
            assert False, "Couldn't determine if repo is an application or a library"
