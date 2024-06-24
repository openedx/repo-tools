
import ast
import re

from os import listdir
from os.path import join
from genericpath import isdir, isfile

from config import blacklist

# can't use ast because .py files include invalid identifier e.g. {{cookiecutter.class_name}}
def parse_imports(path):
    """
    parses `path` as a python file and returns the list of all the modules
    imported in the file. Any sub-modules imported will be ignored and the
    base module will be considered.
    """
    with open(path) as fh:  
        root = ast.parse(fh.read(), path)

    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.Import):
            # import package.module -> package
            module = node.names[0].name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # from package.module import name, othername -> package
            module = node.module.split('.')[0]
        else:
            continue
        yield module


def manually_parse_imports(path):
    """
    parses `path` as a python file and returns the list of all the modules
    imported in the file. Any sub-modules imported will be ignored and the
    base module will be considered.
    """
    import_match  = re.compile("^(from|import)")
    from_import = re.compile('^from (.*) import')
    package_import = re.compile('^import (.*)')

    with open(path) as f:
        isdocstring = False
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('"""'):
                isdocstring = not isdocstring
                continue
            if isdocstring:
                continue
            if line.startswith('#'):
                continue
            if import_match.match(line) is None:
                # we don't support imports anywhere other then the top of file
                break

            package = from_import.match(line) if line.startswith('from') else package_import.match(line)
            yield package.groups()[0].split(' ')[0].split('.')[0]

def gather_imports( path, imports = set()):
    """
    Walks `path` recursively and parses each .py file to generate a set of
    all the imports.
    """
    content = listdir(path)
    files = [f for f in content if isfile(join(path, f))]
    for file in files:
        if file.endswith('.py'):
            imports.update(manually_parse_imports(join(path, file)))

    dirs = {d for d in content if isdir(join(path, d))}
    for dir in dirs - blacklist:
        gather_imports(join(path, dir))

    return imports