"""Send email through the Gmail API.

Required environment variables (copy the values from the token.json made by get_token.py):
    GMAIL_CLIENT_ID
    GMAIL_CLIENT_SECRET
    GMAIL_REFRESH_TOKEN
Optional:
    GMAIL_SENDER_NAME     display name for the From line, e.g. "Coco Cafe Events"
    GMAIL_SENDER_ADDRESS  the Gmail address you signed in with (needed with the name above)

Emails are sent on a background thread so a slow or failed send never blocks or breaks
the web request. Failures are logged, not raised.
"""
import base64
import logging
import os
import threading
from email.message import EmailMessage
from email.utils import formataddr

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
_service = None
_lock = threading.Lock()


def email_configured():
    return all(os.environ.get(k) for k in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"))


def _get_service():
    """Build the Gmail client once and reuse it; the library refreshes the access token itself."""
    global _service
    with _lock:
        if _service is None:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
                client_id=os.environ["GMAIL_CLIENT_ID"],
                client_secret=os.environ["GMAIL_CLIENT_SECRET"],
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES,
            )
            _service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return _service


def _send_now(to, subject, body):
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    sender_name = os.environ.get("GMAIL_SENDER_NAME")
    sender_address = os.environ.get("GMAIL_SENDER_ADDRESS")
    if sender_name and sender_address:
        msg["From"] = formataddr((sender_name, sender_address))
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    with _lock:  # the Google client is not thread-safe, so send one at a time
        result = _service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id")


def _worker(to, subject, body):
    try:
        _get_service()
        msg_id = _send_now(to, subject, body)
        log.info("Email sent to %s (%s): %s", to, msg_id, subject)
    except Exception as exc:  # RefreshError here means the refresh token needs replacing
        log.error("Email to %s failed: %s", to, exc)


def send_email(to, subject, body):
    """Queue an email to send in the background. Returns immediately."""
    if not to:
        return
    if not email_configured():
        log.warning("Gmail not configured; skipped email to %s: %s", to, subject)
        return
    threading.Thread(target=_worker, args=(to, subject, body), daemon=True).start()
