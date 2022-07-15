import click

from edx_repo_tools.utils import YamlLoader

ADD_NEW_FIELDS = ["github-actions"]


class YamlModernizer(YamlLoader):
    """
    Yaml Modernizer class is responsible for getting rid of obsolete elements from openedx.yaml files
    update the DEPRECATED_FIELDS list to adjust the modernizer output
    """

    def __init__(self, file_path):
        super().__init__(file_path)

    def _add_elements(self):
        for _field in ADD_FIELDS:
            if deprecated_field in self.elements.keys():
                del self.elements[deprecated_field]

    def modernize(self):
        self._add_elements()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='openedx.yaml',
    help="Path to target openedx.yaml file")
def main(path):
    import pdb;
    pdb.set_trace()
    modernizer = YamlModernizer(path)
    modernizer.modernize()


if __name__ == "__main__":
    main()
