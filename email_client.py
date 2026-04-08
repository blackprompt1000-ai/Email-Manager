"""
email_client.py — Real email integration via IMAP.

Connects to real email providers (Gmail, Outlook, Yahoo, custom IMAP),
fetches inbox emails, parses them, and supports actions (delete, move to trash).
"""

import email
import email.utils
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from typing import Optional


# ── Provider Presets ──────────────────────────────

PROVIDER_PRESETS = {
    "gmail": {"host": "imap.gmail.com", "port": 993},
    "outlook": {"host": "imap-mail.outlook.com", "port": 993},
    "yahoo": {"host": "imap.mail.yahoo.com", "port": 993},
    "hotmail": {"host": "imap-mail.outlook.com", "port": 993},
    "icloud": {"host": "imap.mail.me.com", "port": 993},
}


def _decode_header_value(value: str) -> str:
    """Decode email header value handling encoded words."""
    if value is None:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _extract_text_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")

        # Fallback: try text/html
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_text = payload.decode(charset, errors="replace")
                    # Strip HTML tags for plain text
                    clean = re.sub(r"<[^>]+>", " ", html_text)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    return clean
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")

    return "(No body content)"


def _parse_date(date_str: str) -> str:
    """Parse email date string into readable format."""
    if not date_str:
        return "Unknown"
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return date_str[:30] if date_str else "Unknown"


class EmailClient:
    """IMAP Email Client for fetching and managing real emails."""

    def __init__(self, email_address: str, password: str, provider: str = "gmail",
                 host: str = None, port: int = None):
        self.email_address = email_address
        self.password = password

        # Resolve IMAP server
        preset = PROVIDER_PRESETS.get(provider.lower(), {})
        self.host = host or preset.get("host", "")
        self.port = port or preset.get("port", 993)

        if not self.host:
            raise ValueError(f"Unknown provider '{provider}'. Provide host manually.")

        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> dict:
        """Connect to the IMAP server and authenticate."""
        try:
            self._connection = imaplib.IMAP4_SSL(self.host, self.port)
            self._connection.login(self.email_address, self.password)
            return {"success": True, "message": "Connected successfully!"}
        except imaplib.IMAP4.error as e:
            err_msg = str(e)
            if "AUTHENTICATIONFAILED" in err_msg.upper() or "AUTHENTICATE" in err_msg.upper():
                return {
                    "success": False,
                    "message": "Authentication failed. Check your email and app password. "
                               "For Gmail, use an App Password (not your regular password)."
                }
            return {"success": False, "message": f"IMAP error: {err_msg}"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def disconnect(self):
        """Close the IMAP connection."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def fetch_emails(self, count: int = 100, folder: str = "INBOX") -> dict:
        """
        Fetch the latest N emails from the inbox.

        Returns dict with 'success', 'emails' list, and 'message'.
        """
        if not self._connection:
            return {"success": False, "emails": [], "message": "Not connected. Please connect first."}

        try:
            status, _ = self._connection.select(folder, readonly=True)
            if status != "OK":
                return {"success": False, "emails": [], "message": f"Could not select folder: {folder}"}

            # Search for all emails
            status, data = self._connection.search(None, "ALL")
            if status != "OK":
                return {"success": False, "emails": [], "message": "Failed to search emails."}

            email_ids = data[0].split()
            if not email_ids:
                return {"success": True, "emails": [], "message": "Inbox is empty."}

            # Get latest N emails (most recent first)
            latest_ids = email_ids[-count:]
            latest_ids.reverse()

            emails = []
            for eid in latest_ids:
                try:
                    status, msg_data = self._connection.fetch(eid, "(RFC822)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    sender = _decode_header_value(msg.get("From", ""))
                    subject = _decode_header_value(msg.get("Subject", "(No Subject)"))
                    date_str = msg.get("Date", "")
                    body = _extract_text_body(msg)

                    # Truncate body for display
                    if len(body) > 1000:
                        body = body[:1000] + "..."

                    emails.append({
                        "id": eid.decode("utf-8"),
                        "sender": sender,
                        "subject": subject,
                        "body": body,
                        "date": _parse_date(date_str),
                        "raw_date": date_str,
                    })
                except Exception:
                    continue

            return {
                "success": True,
                "emails": emails,
                "message": f"Fetched {len(emails)} emails.",
            }

        except Exception as e:
            return {"success": False, "emails": [], "message": f"Fetch error: {str(e)}"}

    def fetch_all_emails_batched(self, batch_size: int = 50,
                                   max_emails: int = 500,
                                   progress_callback=None) -> dict:
        """
        Fetch ALL emails from inbox using batched UID iteration.

        Args:
            batch_size:        How many emails to fetch per IMAP round-trip.
            max_emails:        Cap total emails to protect memory (default 500).
            progress_callback: Callable(fetched: int, total: int) called after each batch.

        Returns:
            {"success": bool, "emails": list, "message": str}
        """
        if not self._connection:
            return {"success": False, "emails": [], "message": "Not connected. Please connect first."}

        try:
            status, _ = self._connection.select("INBOX", readonly=True)
            if status != "OK":
                return {"success": False, "emails": [], "message": "Cannot open INBOX folder."}

            status, data = self._connection.search(None, "ALL")
            if status != "OK":
                return {"success": False, "emails": [], "message": "Failed to search emails."}

            all_ids = data[0].split()
            if not all_ids:
                return {"success": True, "emails": [], "message": "Inbox is empty."}

            # Cap and reverse so newest come first
            all_ids = all_ids[-max_emails:]
            all_ids.reverse()
            total = len(all_ids)

            if progress_callback:
                progress_callback(0, total)

            emails = []
            for batch_start in range(0, total, batch_size):
                batch = all_ids[batch_start: batch_start + batch_size]
                for eid in batch:
                    try:
                        status, msg_data = self._connection.fetch(eid, "(RFC822)")
                        if status != "OK":
                            continue
                        raw = msg_data[0][1]
                        msg = email.message_from_bytes(raw)

                        sender  = _decode_header_value(msg.get("From", ""))
                        subject = _decode_header_value(msg.get("Subject", "(No Subject)"))
                        body    = _extract_text_body(msg)
                        if len(body) > 1000:
                            body = body[:1000] + "..."

                        emails.append({
                            "id":       eid.decode("utf-8"),
                            "sender":   sender,
                            "subject":  subject,
                            "body":     body,
                            "date":     _parse_date(msg.get("Date", "")),
                            "raw_date": msg.get("Date", ""),
                        })
                    except Exception:
                        continue

                if progress_callback:
                    progress_callback(min(batch_start + batch_size, total), total)

            return {
                "success": True,
                "emails":  emails,
                "message": f"Fetched {len(emails)} emails.",
            }

        except Exception as e:
            return {"success": False, "emails": [], "message": f"Batch fetch error: {str(e)}"}

    def delete_email(self, email_id: str, folder: str = "INBOX") -> dict:
        """Move an email to Trash (mark as deleted)."""
        if not self._connection:
            return {"success": False, "message": "Not connected."}

        try:
            self._connection.select(folder, readonly=False)
            self._connection.store(email_id.encode(), "+FLAGS", "\\Deleted")
            self._connection.expunge()
            return {"success": True, "message": "Email deleted successfully."}
        except Exception as e:
            return {"success": False, "message": f"Delete failed: {str(e)}"}

    def move_to_spam(self, email_id: str, folder: str = "INBOX") -> dict:
        """Move an email to Spam/Junk folder."""
        if not self._connection:
            return {"success": False, "message": "Not connected."}

        try:
            self._connection.select(folder, readonly=False)
            # Try common spam folder names
            spam_folders = ["[Gmail]/Spam", "Junk", "Spam", "Bulk Mail", "INBOX.Junk"]
            moved = False
            for spam_folder in spam_folders:
                try:
                    result = self._connection.copy(email_id.encode(), spam_folder)
                    if result[0] == "OK":
                        self._connection.store(email_id.encode(), "+FLAGS", "\\Deleted")
                        self._connection.expunge()
                        moved = True
                        break
                except Exception:
                    continue

            if moved:
                return {"success": True, "message": "Email moved to spam."}
            else:
                # Fallback: just flag as spam
                self._connection.store(email_id.encode(), "+FLAGS", "\\Flagged")
                return {"success": True, "message": "Email flagged (spam folder not found)."}
        except Exception as e:
            return {"success": False, "message": f"Move to spam failed: {str(e)}"}
