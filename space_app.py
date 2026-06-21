#!/usr/bin/env python3
"""Minimal web server that runs the Hermes Agent landing page as a Space.

This lets the repository run as a Hugging Face Docker Space with Spaces Dev
Mode support. It simply serves the static assets in ``landingpage/`` over HTTP
on the port Hugging Face expects (7860 by default).

For full agent usage, open a Dev Mode terminal (SSH or VS Code), install the
package with ``pip install -e ".[all]"`` and run the ``hermes`` CLI as
documented in the README.
"""

import http.server
import os

PORT = int(os.environ.get("PORT", "7860"))
HERE = os.path.dirname(os.path.abspath(__file__))
WEBROOT = os.path.join(HERE, "landingpage")


def main() -> None:
    handler_class = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=WEBROOT, **kwargs
    )
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), handler_class)
    print(f"Serving Hermes Agent landing page on http://0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
