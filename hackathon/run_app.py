"""
run_app.py — Launch Email Rectifier as a standalone desktop application.

Uses pywebview to wrap the Flask server in a native OS window.
No browser needed — just run:  python run_app.py
"""

import sys
import time
import socket
import threading
import webview
from app import app

PORT = 5000
HOST = "127.0.0.1"


def _port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0


def _wait_for_server(timeout: int = 15) -> bool:
    """Block until the Flask server is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        if _port_in_use(PORT):
            return True
        time.sleep(0.15)
    return False


def start_flask():
    """Start the Flask server in a background thread (silent, no browser)."""
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)          # suppress request logs in the console

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    # 0. Check for port conflict
    if _port_in_use(PORT):
        print(f"[!] Port {PORT} is already in use. Close other instances first.")
        sys.exit(1)

    # 1. Start Flask in a background daemon thread
    server = threading.Thread(target=start_flask, daemon=True)
    server.start()

    # 2. Wait until Flask is ready before opening the window
    print("[*] Starting Email Rectifier - AI Email Assistant...")
    if not _wait_for_server():
        print("[!] Server did not start in time. Exiting.")
        sys.exit(1)
    print(f"[OK] Server ready on {HOST}:{PORT}")

    # 3. Open a native desktop window pointing at the Flask app
    window = webview.create_window(
        title="Email Rectifier — AI Email Assistant",
        url=f"http://{HOST}:{PORT}",
        width=1340,
        height=860,
        min_size=(960, 640),
        resizable=True,
        text_select=True,
    )
    webview.start()          # Blocks until the window is closed
    print("[*] Application closed.")
