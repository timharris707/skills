"""The Advisory Board conductor, split into cohesive modules.

``run_board.py`` is a thin façade that re-exports this package's
public API; the import order (constants -> registry -> ... -> cli)
follows the module dependency DAG. See ../README.md for the layout.
"""
