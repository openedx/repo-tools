import sys
from lib2to3.fixer_util import Name, KeywordArg, Comma
from typing import Optional

from bowler import Query, LN, Capture, Filename, TOKEN
from fissix.pytree import Leaf


def render_has_no_renderer(node: LN, capture: Capture, filename: Filename) -> bool:

    if 'function_def' not in capture:
        return False  # This is not a function definition, no need to add argument

    arguments = capture.get("function_arguments")[0].children

    known_arguments = [arg.value for arg in arguments if arg.value in ['name', 'value', 'attrs']]
    if len(known_arguments) != 3:
        return False  # This render doesn't belong to widget

    for arg in arguments:
        if arg.type == TOKEN.NAME and arg.value == "renderer":
            return False  # This definition already has a renderer argument.

    return True


def add_renderer(node: LN, capture: Capture, filename: Filename) -> Optional[LN]:
    arguments = capture.get("function_arguments")[0]
    new_renderer_node = KeywordArg(Name(" renderer"), Name("None"))

    if isinstance(arguments, Leaf):  # Node is a leaf and so we need to replace it with a list of things we want instead
        arguments.replace([arguments.clone(), Comma(), new_renderer_node])
    else:
        arguments.append_child(Comma())
        arguments.append_child(new_renderer_node)

    return node


(
    Query(sys.argv[1])
        .select_method("render")
        .filter(render_has_no_renderer)
        .modify(add_renderer)
        .idiff()
)
