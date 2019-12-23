import sys

from typing import Optional
from bowler import Query, LN, Capture, Filename, TOKEN, SYMBOL
from fissix.pytree import Node, Leaf


# usage of the User.is_authenticated() and User.is_anonymous() methods is deprecated. Remove the last parenthesis.


def parentheses(node: LN, capture: Capture, filename: Filename) -> Optional[LN]:

    # this is how the last node look a like, Node(trailer, [Leaf(7, '('), Leaf(8, ')')])
    nodes = capture.get("function_call")
    last_node = nodes.children[-1]  # pick the last node

    # make sure its a leaf and contains parenthesis before deleting the last node
    if isinstance(last_node.children[0], Leaf) and isinstance(last_node.children[1], Leaf):
        if last_node.children[0].value == "(" and last_node.children[1].value == ")":
            del nodes.children[-1]

    return nodes


(
    Query(sys.argv[1])
    .select_method("is_authenticated")
    .modify(parentheses)
    .idiff()
),
(
    Query(sys.argv[1])
    .select_method("is_anonymous")
    .modify(parentheses)
    .idiff()
)
