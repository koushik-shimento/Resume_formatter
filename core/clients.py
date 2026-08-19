"""Registry of client output formats shown in the dropdown.

To add a client: write a module with a `render(data, out_path)` function and a
`DISPLAY_NAME`, then add it below.
"""

from . import render_shimentox

_MODULES = (render_shimentox,)

CLIENTS = {m.DISPLAY_NAME: m for m in _MODULES}


def names() -> list[str]:
    return list(CLIENTS)


def render(client: str, data, out_path):
    return CLIENTS[client].render(data, out_path)
