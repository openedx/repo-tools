import click

from edx_repo_tools.utils import YamlLoader


github_actions = """\
    # Adding new check for github-actions
    package-ecosystem": github-actions
    directory: /
    schedule:
        interval: weekly
"""

# Adding new packages for update. Add tuple with key and related data.
ADD_NEW_FIELDS = [("github-actions", github_actions,)]


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
            self.elements['updates'].append(self.yml_instance.load(value))

    def modernize(self):
        self._add_elements()
        # otherwise it brings back whole update back towards left side.

        self.yml_instance.indent(mapping=4, sequence=4, offset=2)
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
