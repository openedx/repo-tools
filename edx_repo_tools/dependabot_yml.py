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

# Adding new packages for update. Add tuple with key and related data.
ADD_NEW_FIELDS = [("github-actions", github_actions,)]


class DependabotYamlModernizer(YamlLoader):
    """
    Dependabot Yaml Modernizer class is responsible for adding new elements in dependabot.yml.
    """

    def __init__(self, file_path):
        super().__init__(file_path)

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

    def modernize(self):
        self._add_elements()
        # otherwise it brings back whole update back towards left side.

        self.yml_instance.indent(mapping=4, sequence=4, offset=2)
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='.github/dependabot.yml',
    help="Path to target dependabot.yml file")
def main(path):
    if not os.path.exists(path):
        new_file_content = """\
            version: 2
            updates:
        """
        with open(path, 'w') as file:
            file.write(new_file_content)
    modernizer = DependabotYamlModernizer(path)
    modernizer.modernize()


if __name__ == "__main__":
    main()
