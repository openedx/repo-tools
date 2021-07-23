import click

from edx_repo_tools.utils import YamlLoader

DEPRECATED_FIELDS = ['owner', 'supporting_teams', 'track_pulls', 'track-pulls']


class YamlModernizer(YamlLoader):
    """
    Yaml Modernizer class is responsible for getting rid of obsolete elements from openedx.yaml files
    update the DEPRECATED_FIELDS list to adjust the modernizer output
    """

    def __init__(self, file_path):
        super().__init__(file_path)

    def _remove_deprecated_elements(self):
        for deprecated_field in DEPRECATED_FIELDS:
            if deprecated_field in self.elements.keys():
                del self.elements[deprecated_field]

    def modernize(self):
        self._remove_deprecated_elements()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='openedx.yaml',
    help="Path to target openedx.yaml file")
def main(path):
    modernizer = YamlModernizer(path)
    modernizer.modernize()


if __name__ == "__main__":
    main()
