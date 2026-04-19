"""Fixture: Python file with known cyclomatic complexity values for test assertions."""


def simple_function(x):
    """CC=1 — straight-line, no branches."""
    return x * 2


def branchy_function(a, b, c):
    """CC=4 — one if/elif/else chain."""
    if a > 0:
        return a
    elif b > 0:
        return b
    elif c > 0:
        return c
    else:
        return 0


def complex_function(items, threshold, mode):
    """CC=7 — nested conditionals + loop."""
    result = []
    for item in items:
        if mode == "strict":
            if item > threshold:
                result.append(item)
            elif item == threshold:
                result.append(item * 2)
        elif mode == "loose":
            if item >= threshold / 2:
                result.append(item)
        else:
            result.append(item)
    return result
