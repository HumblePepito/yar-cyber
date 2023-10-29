from typing import Tuple

import numpy as np 


# Fire line struct used for statically defined the fire line. Used in calculation.
line_dt = np.dtype(
    [
        ("clear", bool),  # True if this tile is empty.
        ("path", "2B"), # tuples of coordinates between start and end point
        ("cover", np.int32),  # Percentage of cover each tile provides
    ]
)


def new_line(
    *,  # Enforce the use of keywords, so that parameter order doesn't matter.
    clear: bool,
    path: Tuple[int, int],
    cover: int,
) -> np.ndarray:
    """Helper function for defining individual tile types """
    return np.array((clear, path, cover), dtype=line_dt)

default = new_line(
    clear=True, path=(1,1), cover=0,
)
