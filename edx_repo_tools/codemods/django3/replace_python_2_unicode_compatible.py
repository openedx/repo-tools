"""
A script to remove the python2_unicode_compatible imports and headers
"""
import sys
from bowler import Query


def remove_node(node, _, __):
    """
    Remove the node containing the expression python_2_unicode_compatible
    """
    node.remove()


(
    Query(sys.argv[1])
    .select("decorator<'@' name='python_2_unicode_compatible' any>")
    .modify(remove_node)
    .select("import_from<'from' module_name=any 'import' 'python_2_unicode_compatible'>")
    .modify(remove_node)
    .write()
)
