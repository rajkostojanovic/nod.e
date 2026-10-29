from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LEADS_FILE = DATA_DIR / "leads.json"


def ensure_store() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not LEADS_FILE.exists():
        LEADS_FILE.write_text("[]", encoding="utf-8")


def append_record(payload: dict) -> None:
    try:
        raw = LEADS_FILE.read_text(encoding="utf-8")
        items = json.loads(raw) if raw else []
    except (json.JSONDecodeError, OSError):
        items = []

    payload["receivedAt"] = datetime.now(timezone.utc).isoformat()
    items.append(payload)
    LEADS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def send_email(sender: str, sender_email: str, message: str) -> None:
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    mail_to = os.getenv("MAIL_TO", "rajkostojanovic@gmail.com")

    if not smtp_user or not smtp_pass:
        raise RuntimeError("Missing SMTP_USER or SMTP_PASS environment variables.")

    email_msg = EmailMessage()
    email_msg["Subject"] = f"nod.e contact from {sender or sender_email}"
    email_msg["From"] = smtp_user
    email_msg["To"] = mail_to
    if sender_email:
        email_msg["Reply-To"] = sender_email

    email_msg.set_content(
        "\n".join(
            [
                f"Sender: {sender}",
                f"Email: {sender_email}",
                "",
                message,
            ]
        )
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        smtp.send_message(email_msg)


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/api/lead":
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = parse_qs(body)

        sender = (data.get("sender") or [""])[0].strip()
        message = (data.get("message") or [""])[0].strip()
        email = (data.get("email") or [""])[0].strip()

        if not sender or not email or not message:
            self.send_error(400, "Sender, email, and message are required.")
            return

        append_record({"sender": sender, "message": message, "email": email})

        try:
            send_email(sender, email, message)
        except Exception as exc:
            self.send_error(500, f"Email send failed: {exc}")
            return

        self.send_response(303)
        self.send_header("Location", "/contact.html")
        self.end_headers()


if __name__ == "__main__":
    ensure_store()
    server = ThreadingHTTPServer(("0.0.0.0", 8000), lambda *args, **kwargs: Handler(*args, directory=str(BASE_DIR), **kwargs))
    print("Serving nod.e on http://localhost:8000")
    server.serve_forever()
