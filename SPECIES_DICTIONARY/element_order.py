"""Shared thermochemistry element order.

The order below is used to build sum formulas for InChI cross-checking.
Do not reorder these symbols unless you intentionally update the
species-dictionary formula comparison behavior across the project.
"""

THERMO_SUM_FORMULA_ELEMENT_ORDER = (
    "C",
    "H",
    "F",
    "N",
    "O",
    "S",
    "CL",
    "HE",
    "AR",
    "E",
)

THERMO_SUM_FORMULA_ELEMENTS = {
    elem: 1
    for elem in THERMO_SUM_FORMULA_ELEMENT_ORDER
}
