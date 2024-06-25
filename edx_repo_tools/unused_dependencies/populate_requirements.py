
from os import walk
from os.path import join


def populate_requirements(path, requirements = set()):
    """
    returns a set of all the requirements listed in any .in file inside
    `path`. The version numbers and comments are removed from the returned
    set.
    """
    for dirpath, dirs, files in walk(path):
        for file in files:
            if file.endswith('.in'):
                filepath = join(dirpath, file)
                with open(filepath) as req_file:
                    # `package=10.3 # some comments` -> package
                    requirements.update(package.split(' ')[0].split('=')[0].strip('\n') for package in req_file if package[0] not in ['#', '-', '\n', ' '])
        for dir in dirs:
            populate_requirements(join(dirpath, dir), requirements)
    
    return requirements