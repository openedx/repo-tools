import sys
from lib2to3.fixer_util import Name, Comma
from typing import Optional

from bowler import Query, LN, Capture, Filename

DJANGO_SHORTCUT_FILES = []


def filter_render_function(node: LN, capture: Capture, filename: Filename) -> bool:
    import_statement = capture.get("function_import")
    function_call = capture.get("function_call")
    if import_statement:
        if "django.shortcuts" in str(import_statement.children[1]):
            DJANGO_SHORTCUT_FILES.append(filename)
            return True
    elif function_call:
        # Only rename and modify those render_to_response which are imported from django.shortcuts
        return filename in DJANGO_SHORTCUT_FILES

    return False


def add_request_param(node: LN, capture: Capture, filename: Filename) -> Optional[LN]:
    arguments = capture.get("function_arguments")
    if arguments:
        arguments = arguments[0]
        # Insert request parameter at start
        arguments.insert_child(0, Name("request"))
        arguments.insert_child(1, Comma())
        arguments.children[2].prefix = " "

    return node


def main():
    (
        Query(sys.argv[1])
            .select_function("render_to_response")
            .filter(filter_render_function)
            .rename('render')
            .modify(add_request_param)
            .write()
    )


if __name__ == '__main__':
    main()
