# ============================================================
# Application entry point.
#
# Creates a single native window pointing at the bundled local HTML and
# wires the Api bridge. No HTTP server is started and no network port is
# opened: the UI is loaded from the local file system and Python is
# reached only through the in-process js_api bridge.
#
# Run in development with:  python app.py
# ============================================================

from __future__ import annotations

import os

import webview

from api import Api, resource_path

WINDOW_TITLE = "NeuroCogProfile"


def main() -> None:
    """Create the window, attach the API, and start the event loop."""
    api = Api()
    index_html = resource_path(os.path.join("web", "index.html"))

    window = webview.create_window(
        WINDOW_TITLE,
        url=index_html,
        js_api=api,
        width=1240,
        height=880,
        min_size=(980, 640),
    )
    api.set_window(window)

    # debug=False and no http_server: fully local, no network access.
    webview.start()


if __name__ == "__main__":
    main()
