"""
Kite Connect Authentication Module.

This module provides easy authentication for Kite Connect API by:
1. Opening the login URL in user's default browser
2. Running a local callback server to capture the redirect
3. Exchanging request_token for access_token
4. Saving the session for reuse

:copyright: (c) 2025
:license: MIT

Usage::

    from src.brokers.kite import KiteAuth

    auth = KiteAuth()
    access_token = auth.login()


    client = auth.get_client()
"""

import os
import json
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ...config import get_config
from .client import KiteClient

log = logging.getLogger(__name__)

TOKEN_FILE = Path(".kite_session.json")
DEFAULT_REDIRECT_PORT = 5000


class CallbackHandler(BaseHTTPRequestHandler):
    """
    HTTP handler to capture OAuth redirect with request_token.

    :cvar request_token: Captured request token from redirect.
    :cvar error: Error message if login failed.
    """

    request_token: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self) -> None:
        """
        Handle GET request from Kite redirect.

        :returns: None
        :rtype: None
        """
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "request_token" in params:
            CallbackHandler.request_token = params["request_token"][0]
            self._send_success_response()
        elif "error" in params:
            CallbackHandler.error = params.get("message", ["Login failed"])[0]
            self._send_error_response(CallbackHandler.error)
        else:
            self._send_error_response("No request_token in callback")

    def _send_success_response(self) -> None:
        """
        Send success HTML response.

        :returns: None
        :rtype: None
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg,
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 40px 60px;
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
                .checkmark {
                    font-size: 64px;
                    color:
                }
                h1 { color:
                p { color:
                .close-msg { margin-top: 20px; font-size: 14px; color:
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✓</div>
                <h1>Login Successful!</h1>
                <p>You can close this window and return to your application.</p>
                <p class="close-msg">This window will close automatically...</p>
            </div>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str) -> None:
        """
        Send error HTML response.

        :param error: Error message to display.
        :type error: str
        :returns: None
        :rtype: None
        """
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg,
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px 60px;
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .error-icon {{ font-size: 64px; color:
                h1 {{ color:
                p {{ color:
                .error-msg {{ color:
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✗</div>
                <h1>Login Failed</h1>
                <p class="error-msg">{error}</p>
                <p style="margin-top: 20px;">Please login to <a href="https://kite.zerodha.com">kite.zerodha.com</a> first, then try again.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""


class KiteAuth:
    """
    Kite Connect authentication manager.

    Opens login URL in browser and captures redirect to get access token.
    If user is already logged into Kite in browser, it auto-redirects.

    :param api_key: Kite API key.
    :type api_key: Optional[str]
    :param api_secret: Kite API secret.
    :type api_secret: Optional[str]
    :param redirect_port: Port for local callback server.
    :type redirect_port: int

    Example::

        auth = KiteAuth()


        token = auth.login()


        client = auth.get_client()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        redirect_port: int = DEFAULT_REDIRECT_PORT,
    ) -> None:
        """
        Initialize authentication manager.

        :param api_key: Kite API key (or from KITE_API_KEY env).
        :type api_key: Optional[str]
        :param api_secret: Kite API secret (or from KITE_API_SECRET env).
        :type api_secret: Optional[str]
        :param redirect_port: Local port for OAuth callback.
        :type redirect_port: int
        """
        config = get_config()

        self.api_key = api_key or config.api_key
        self.api_secret = api_secret or os.getenv("KITE_API_SECRET", "")
        self.redirect_port = redirect_port
        self.redirect_url = f"http://127.0.0.1:{redirect_port}"
        self._client: Optional[KiteClient] = None

    def _load_saved_session(self) -> Optional[Dict[str, Any]]:
        """
        Load saved session from file if still valid.

        :returns: Session data if valid, None otherwise.
        :rtype: Optional[Dict[str, Any]]
        """
        if not TOKEN_FILE.exists():
            return None

        try:
            data = json.loads(TOKEN_FILE.read_text())
            expiry = datetime.fromisoformat(data.get("expiry", ""))

            if datetime.now() < expiry:
                log.info("Using saved session (valid until %s)", expiry)
                return data
            else:
                log.info("Saved session expired at %s", expiry)
                return None
        except Exception as e:
            log.warning("Failed to load saved session: %s", e)
            return None

    def _save_session(self, access_token: str, user_data: Dict[str, Any]) -> None:
        """
        Save session to file for reuse.

        Token expires at 6 AM IST daily.

        :param access_token: The access token to save.
        :type access_token: str
        :param user_data: User session data from API.
        :type user_data: Dict[str, Any]
        """
        today_6am = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        if datetime.now().hour >= 6:
            expiry = today_6am + timedelta(days=1)
        else:
            expiry = today_6am

        session_data = {
            "access_token": access_token,
            "user_id": user_data.get("user_id"),
            "user_name": user_data.get("user_name"),
            "email": user_data.get("email"),
            "expiry": expiry.isoformat(),
            "created_at": datetime.now().isoformat(),
        }

        TOKEN_FILE.write_text(json.dumps(session_data, indent=2))
        log.info("Session saved (expires: %s)", expiry)

    def _get_login_url(self) -> str:
        """
        Get Kite login URL with redirect.

        :returns: Login URL.
        :rtype: str
        """
        return (
            f"https://kite.zerodha.com/connect/login"
            f"?api_key={self.api_key}"
            f"&v=3"
            f"&redirect_params=true"
        )

    def _wait_for_callback(self, timeout: int = 120) -> str:
        """
        Start local server and wait for OAuth callback.

        :param timeout: Timeout in seconds.
        :type timeout: int
        :returns: Request token from callback.
        :rtype: str
        :raises TimeoutError: If no callback received.
        :raises RuntimeError: If login was rejected.
        """
        CallbackHandler.request_token = None
        CallbackHandler.error = None

        server = HTTPServer(("127.0.0.1", self.redirect_port), CallbackHandler)
        server.timeout = timeout

        log.info("Waiting for login callback on port %d...", self.redirect_port)

        server.handle_request()
        server.server_close()

        if CallbackHandler.error:
            raise RuntimeError(
                f"Login failed: {CallbackHandler.error}\n\n"
                "Please login to Kite first:\n"
                "  1. Open https://kite.zerodha.com in your browser\n"
                "  2. Login with your Zerodha credentials\n"
                "  3. Run this auth module again\n"
            )

        if not CallbackHandler.request_token:
            raise TimeoutError(
                "No login callback received.\n"
                "Make sure you complete the login in your browser."
            )

        return CallbackHandler.request_token

    def login(self, force: bool = False) -> str:
        """
        Perform login and get access token.

        1. Checks for valid saved session
        2. If none, opens browser for login
        3. If already logged into Kite, auto-redirects
        4. Captures redirect and exchanges for access_token
        5. Saves session for future use

        :param force: Force new login even if session exists.
        :type force: bool
        :returns: Valid access token.
        :rtype: str
        :raises ValueError: If credentials missing.
        :raises RuntimeError: If login fails.

        Example::

            auth = KiteAuth()
            token = auth.login()
            print(f"Access token: {token[:20]}...")
        """
        if not force:
            saved = self._load_saved_session()
            if saved:
                return saved["access_token"]

        if not self.api_key:
            raise ValueError("KITE_API_KEY not set. Add it to your .env file.")

        if not self.api_secret:
            raise ValueError("KITE_API_SECRET not set. Add it to your .env file.")

        login_url = self._get_login_url()

        print("\n" + "=" * 60)
        print("KITE LOGIN")
        print("=" * 60)
        print("\nOpening browser for Kite login...")
        print("\nIf you're already logged into Kite, it will auto-redirect.")
        print("Otherwise, please login with your Zerodha credentials.")
        print("\nIf browser doesn't open, visit this URL manually:")
        print(f"\n  {login_url}\n")
        print("=" * 60 + "\n")

        webbrowser.open(login_url)

        request_token = self._wait_for_callback()
        log.info("Got request token: %s...", request_token[:10])

        client = KiteClient(api_key=self.api_key)
        session_data = client.generate_session(request_token, self.api_secret)

        access_token = session_data.get("access_token")
        if not access_token:
            raise RuntimeError("No access_token in session response")

        self._save_session(access_token, session_data)
        self._client = client

        print("\n✓ Login successful!")
        print(
            f"  User: {session_data.get('user_name')} ({session_data.get('user_id')})"
        )
        print(f"  Session saved to {TOKEN_FILE}\n")

        return access_token

    def get_client(self, force_login: bool = False) -> KiteClient:
        """
        Get authenticated KiteClient instance.

        :param force_login: Force new login.
        :type force_login: bool
        :returns: Authenticated KiteClient.
        :rtype: KiteClient

        Example::

            auth = KiteAuth()
            client = auth.get_client()
            print(client.profile())
            print(client.positions())
        """
        access_token = self.login(force=force_login)

        if self._client is None:
            self._client = KiteClient(api_key=self.api_key, access_token=access_token)

        return self._client

    def logout(self) -> None:
        """
        Clear saved session file.

        :returns: None
        :rtype: None
        """
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            log.info("Session cleared")
            print("Session cleared.")

    @staticmethod
    def is_logged_in() -> bool:
        """
        Check if a valid session exists.

        :returns: True if valid session exists.
        :rtype: bool
        """
        if not TOKEN_FILE.exists():
            return False

        try:
            data = json.loads(TOKEN_FILE.read_text())
            expiry = datetime.fromisoformat(data.get("expiry", ""))
            return datetime.now() < expiry
        except Exception:
            return False


def auto_login() -> KiteClient:
    """
    Convenience function for quick login.

    :returns: Authenticated KiteClient.
    :rtype: KiteClient

    Example::

        from src.brokers.kite import auto_login

        client = auto_login()
        print(client.positions())
    """
    auth = KiteAuth()
    return auth.get_client()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) > 1 and sys.argv[1] == "logout":
        KiteAuth().logout()
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        if KiteAuth.is_logged_in():
            data = json.loads(TOKEN_FILE.read_text())
            print(f"✓ Logged in as {data.get('user_name')} ({data.get('user_id')})")
            print(f"  Session expires: {data.get('expiry')}")
        else:
            print("✗ Not logged in or session expired")
        sys.exit(0)

    force = len(sys.argv) > 1 and sys.argv[1] == "--force"

    auth = KiteAuth()
    client = auth.get_client(force_login=force)

    profile = client.profile()
    print(f"\nProfile: {profile['user_name']} ({profile['user_id']})")
    print(f"Email: {profile['email']}")
