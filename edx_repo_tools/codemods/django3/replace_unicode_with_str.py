import sys

from bowler import Query


(
    Query(sys.argv[1])
    .select_function("__unicode__")
    .rename('__str__')
    .idiff()
),
(
    Query(sys.argv[1])
    .select_method("__unicode__")
    .is_call()
    .rename('__str__')
    .idiff()
)
