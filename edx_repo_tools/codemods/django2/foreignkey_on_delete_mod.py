import sys

from typing import Optional
from bowler import Query, LN, Capture, Filename, TOKEN, SYMBOL
from fissix.pytree import Node, Leaf
from lib2to3.fixer_util import Name, KeywordArg, Dot, Comma, Newline, ArgList


def filter_print_string(node, capture, filename) -> bool:
    function_name = capture.get("function_name")
    from pprint import pprint

    pprint(node)
    pprint(capture)
    return True


def filter_has_no_on_delete(node: LN, capture: Capture, filename: Filename) -> bool:
    arguments = capture.get("function_arguments")[0].children
    for arg in arguments:
        if arg.type == SYMBOL.argument and arg.children[0].type == TOKEN.NAME:
            arg_name = arg.children[0].value

            if arg_name == "on_delete":
                return False  # this call already has an on_delete argument.
    return True


def add_on_delete_cascade(
    node: LN, capture: Capture, filename: Filename
) -> Optional[LN]:
    arguments = capture.get("function_arguments")[0]
    new_on_delete_node = KeywordArg(Name(" on_delete"), Name("models.CASCADE"))

    if isinstance(arguments, Leaf): # Node is a leaf and so we need to replace it with a list of things we want instead.
        arguments.replace([arguments.clone(),Comma(),new_on_delete_node])
    else: 
        arguments.append_child(Comma())
        arguments.append_child(new_on_delete_node)

    return node


(
    Query(sys.argv[1])
    .select_method("ForeignKey")
    .is_call()
    .filter(filter_has_no_on_delete)
    .modify(add_on_delete_cascade)
    .idiff()
),
(
    Query(sys.argv[1])
    .select_method("OneToOneField")
    .is_call()
    .filter(filter_has_no_on_delete)
    .modify(add_on_delete_cascade)
    .idiff()
)

