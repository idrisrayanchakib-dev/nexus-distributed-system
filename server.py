import http.server
import os
import socketserver
import urllib.parse

PORT = 8080
DIRECTORY = os.path.join(os.path.dirname(__file__), "website")


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Force exact filename for downloadable assets
        parsed = urllib.parse.urlparse(self.path)
        filename = os.path.basename(parsed.path)

        if filename.endswith(".zip"):
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        elif filename.endswith(".exe"):
            self.send_header("Content-Type", "application/vnd.microsoft.portable-executable")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        elif filename.endswith(".svg"):
            self.send_header("Content-Type", "image/svg+xml")

        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"Serving NEXUS Landing Page at http://localhost:{PORT} from {DIRECTORY}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
