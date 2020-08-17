import click
from ruamel.yaml import YAML

DEPRECATED_FIELDS = ['owner', 'supporting_teams', 'track_pulls', 'track-pulls']


class YamlModernizer:
    """
    Yaml Modernizer class is responsible for getting rid of obsolete elements from openedx.yaml files
    update the DEPRECATED_FIELDS list to adjust the modernizer output
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.yml_instance = YAML()
        self.yml_instance.indent(mapping=4, sequence=4, offset=4)

    def _load_file(self):
        with open(self.file_path, 'r') as file_stream:
            self.elements = self.yml_instance.load(file_stream)

    def _remove_deprecated_elements(self):
        for deprecated_field in DEPRECATED_FIELDS:
            if deprecated_field in self.elements.keys():
                del self.elements[deprecated_field]

    def _update_yml_file(self):
        with open(self.file_path, 'w') as file_stream:
            self.yml_instance.dump(self.elements, file_stream)

    def modernize(self):
        self._load_file()
        self._remove_deprecated_elements()
        self._update_yml_file()


@click.command()
@click.option(
    '--path', default='openedx.yaml',
    help="Path to target openedx.yaml file")
def main(path):
    modernizer = YamlModernizer(path)
    modernizer.modernize()


if __name__ == "__main__":
    main()
