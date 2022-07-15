import click

from edx_repo_tools.utils import YamlLoader
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as dq


github_actions = {
    "package-ecosystem": "github-actions",
    "directory": dq("/"),
    "schedule": "",
    "interval": "daily"
}

# Adding new packages for update. Add tuple with key and related data.
ADD_NEW_FIELDS = [("github-actions", github_actions)]


class YamlModernizer(YamlLoader):
    """
    Yaml Modernizer class is responsible for adding new elements in yml.
    """

    def __init__(self, file_path):
        super().__init__(file_path)

    def _add_elements(self):
        updates = self.elements.get('updates')

        found = False
        for key, value in ADD_NEW_FIELDS:
            for index in updates:
                if key in index['package-ecosystem']:
                    found = True
                    break

        if not found:
            self.elements['updates'].append(value)

    def modernize(self):
        self._add_elements()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='dependantbot.yaml',
    help="Path to target dependantbot.yaml file")
def main(path):
    modernizer = YamlModernizer(path)
    modernizer.modernize()


if __name__ == "__main__":
    main()
