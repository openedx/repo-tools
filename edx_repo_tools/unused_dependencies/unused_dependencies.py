from os.path import join, exists

from populate_requirements import populate_requirements
from gather_imports import gather_imports
from config import whitelist


def unused_dependencies(path):
    """
    check for any package listed in any .in file that is not imported in
    any .py file.
    """
    if not exists(path):
        print("Error: {} doesn't exist.".format(path))
        exit(1)
    requirements = populate_requirements(join(path, 'requirements'))
    imports = gather_imports(path)

    # print(requirements)
    # print(imports)
    unused = (requirements - imports) - whitelist
    print(unused)
    # assert len(unused) == 0, "The following packages are unused: {}".format(unused)
