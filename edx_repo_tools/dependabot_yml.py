import os
import click

from edx_repo_tools.utils import YamlLoader


github_actions = """\
    # Adding new check for github-actions
    package-ecosystem: "github-actions"
    directory: "/"
    schedule:
        interval: "weekly"
"""
ecosystem_reviewers = """\
    reviewers:
      - "{reviewer}"
"""

# Adding new packages for update. Add tuple with key and related data.
ADD_NEW_FIELDS = [("github-actions", github_actions,)]


class DependabotYamlModernizer(YamlLoader):
    """
    Dependabot Yaml Modernizer class is responsible for adding new elements in dependabot.yml.
    """

    def __init__(self, file_path, reviewer):
        super().__init__(file_path)
        self.reviewer = reviewer

    def _add_elements(self):
        self.elements['updates'] = self.elements.get('updates') or []
        found = False
        for key, value in ADD_NEW_FIELDS:
            for index in self.elements['updates']:
                if key == index.get('package-ecosystem'):
                    found = True
                    break
        if not found:
            self.elements['updates'].append(self.yml_instance.load(value))

    def _add_reviewers(self):
        self.elements['updates'] = self.elements.get('updates') or []
        for key, value in ADD_NEW_FIELDS:
            for index, elem in enumerate(self.elements['updates']):
                if key == elem.get('package-ecosystem'):
                    self.elements["updates"][index].update(self.yml_instance.load(
                        ecosystem_reviewers.format(**{"reviewer": self.reviewer})
                    ))
                    break


    def modernize(self):
        self._add_elements()
        self.reviewer and self._add_reviewers()
        # otherwise it brings back whole update back towards left side.

        self.yml_instance.indent(mapping=4, sequence=4, offset=2)
        self.update_yml_file()


@click.command()
# path should be the path of dependabot.yml inside a repo
@click.option(
    '--path', default='.github/dependabot.yml',
    help="Path to target dependabot.yml file")
# reviewer should be a github username or team name,
# and the team name should be in the format of org-name/team-name
@click.option(
    '--reviewer', default=None,
    help="Name of the reviewer")
def main(path, reviewer):
    if not os.path.exists(path):
        new_file_content = """\
            version: 2
            updates:
        """
        with open(path, 'w') as file:
            file.write(new_file_content)
    modernizer = DependabotYamlModernizer(path, reviewer)
    modernizer.modernize()


if __name__ == "__main__":
    main()
