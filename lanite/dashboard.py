# dashboard.py — Web-based UI bridge for Lanite 
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional

import history
import settings as cfg

# We will serve the HTML content from this file
HTML_PATH = Path(__file__).parent / 'assets' / 'dashboard.html'


def _find_edge_exe() -> Optional[str]:
    """
    Resolve msedge.exe via the Windows registry so we don't hardcode C:\\Program Files.
    Returns None if Edge is not installed — caller should fall back to webbrowser.
    """
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(
                    hive,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                ) as k:
                    path, _ = winreg.QueryValueEx(k, None)   # default value
                    if path and os.path.exists(path):
                        return path
            except FileNotFoundError:
                continue
    except Exception as e:
        logging.debug(f"Edge registry lookup failed: {e}")
    # Last-ditch: check %ProgramFiles% locations (still portable across drives)
    for env_var in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env_var)
        if base:
            candidate = os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")
            if os.path.exists(candidate):
                return candidate
    return None

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP logs
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_content = ""
            if HTML_PATH.exists():
                try:
                    html_content = HTML_PATH.read_text(encoding='utf-8')
                except Exception as e:
                    html_content = f"<h1>Error reading UI file: {e}</h1>"
            else:
                html_content = f"<h1>UI file not found at {HTML_PATH}</h1>"
                
            self.wfile.write(html_content.encode('utf-8'))
            return

        if self.path == '/lanite_icon.png':
            img_path = HTML_PATH.parent / 'lanite_icon.png'
            if img_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                self.wfile.write(img_path.read_bytes())
                return

        if self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            dashboard = self.server.dashboard_instance
            state = {
                "history": history.get_all(),
                "stats": history.get_stats(),
                "settings": {
                    "remove_fillers": cfg.get("remove_fillers", False),
                    "startup_with_windows": cfg.get("startup_with_windows", False),
                    "trailing_space": cfg.get("trailing_space", True),
                    "language": cfg.get("language", "en"),
                    "model": cfg.get("model", "small.en")
                },
                "status": dashboard.current_status
            }
            self.wfile.write(json.dumps(state).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == '/api/action':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                action = data.get('action')
                dashboard = self.server.dashboard_instance
                
                if action == 'set_setting':
                    key = data.get('key')
                    value = data.get('value')
                    
                    if key == 'startup_with_windows':
                        cfg.set_startup_with_windows(value)
                    else:
                        cfg.set(key, value)
                        
                    if key == 'model' and dashboard._on_model_change:
                        dashboard._on_model_change(value)
                        
                elif action == 'force_stop':
                    if dashboard._on_force_stop:
                        # Call in a separate thread so we can return the HTTP response first
                        threading.Thread(target=dashboard._on_force_stop, daemon=True).start()
                        
            except Exception as e:
                logging.error(f"API action error: {e}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
                return

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            return

        self.send_error(404, "Not Found")


class Dashboard:
    def __init__(
        self,
        root,  # Still accept root to maintain API, but we don't use Tkinter here
        on_force_stop: Callable,
        on_model_change: Optional[Callable] = None,
    ):
        self._on_force_stop = on_force_stop
        self._on_model_change = on_model_change
        
        # Determine status text from root to match initial status
        self.current_status = {"text": "Ready · Ctrl+Win to speak", "color": None}
        self.port = 0
        self.server = None
        self.server_thread = None
        
        # Start the server immediately
        self._start_server()

    def _start_server(self):
        try:
            self.server = ThreadingHTTPServer(('127.0.0.1', 0), DashboardHandler)
            self.server.dashboard_instance = self
            self.port = self.server.server_port
            
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            logging.info(f"Dashboard HTTP server running on port {self.port}")
        except Exception as e:
            logging.error(f"Failed to start dashboard server: {e}")

    def show(self):
        """Show the dashboard using the default browser."""
        if not self.port:
            logging.error("Cannot show dashboard: server is not running.")
            return
            
        url = f"http://127.0.0.1:{self.port}/"
        
        # We run it in a separate thread so it doesn't block
        def _launch():
            import webbrowser, subprocess
            # Prefer Edge in app-mode. Resolve its path via the Windows registry
            # so this works regardless of drive letter or install location.
            edge_exe = _find_edge_exe()
            try:
                if edge_exe:
                    subprocess.Popen([edge_exe, f'--app={url}'])
                else:
                    webbrowser.open(url)
            except Exception as e:
                logging.error(f"Failed to launch browser: {e}")
                try:
                    webbrowser.open(url)
                except Exception as e2:
                    logging.error(f"Fallback browser launch also failed: {e2}")
                
        threading.Thread(target=_launch, daemon=True).start()

    def hide(self):
        # We don't have direct control over the native Edge window to hide it programmatically
        # without complex Win32 APIs, but `hide()` is rarely explicitly needed since 
        # the user typically closes the window manually.
        pass

    def refresh(self):
        # Frontend polling handles refreshing, so this is just a no-op
        pass

    def update_status(self, text: str, color: str = None):
        """Update the status text. Frontend will fetch this."""
        self.current_status = {"text": text, "color": color}
