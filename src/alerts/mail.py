"""Email over Gmail SMTP with an app password (owner decision, 2026-10-17).

The password arrives as the Cloud Run environment value NOWCAST_SMTP_PASSWORD from Secret Manager;
it is never logged, printed or returned. One message per recipient, so no recipient sees another.
"""
import smtplib
import ssl
from email.message import EmailMessage

HOST, PORT = 'smtp.gmail.com', 465


class MailUnavailable(Exception):
    """No sender is configured, or the server refused or could not be reached."""


class SmtpMailer:
    def __init__(self, user, password, host=HOST, port=PORT, timeout=20):
        self.user, self._password, self.host, self.port, self.timeout = user, password, host, port, timeout

    def __repr__(self):
        return f'SmtpMailer({self.user!r}, <password hidden>)'

    def send(self, messages):
        """Send [(to, subject, text, html)] over one connection; returns the addresses accepted."""
        sent = []
        try:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout,
                                  context=ssl.create_default_context()) as server:
                server.login(self.user, self._password)
                for to, subject, text, html in messages:
                    message = EmailMessage()
                    message['From'] = f'Grid Nowcast <{self.user}>'
                    message['To'] = to
                    message['Subject'] = subject
                    message.set_content(text)
                    message.add_alternative(html, subtype='html')
                    server.send_message(message)
                    sent.append(to)
        except (smtplib.SMTPException, OSError):
            if not sent:
                raise MailUnavailable() from None
        return sent


class MemoryMailer:
    """Tests and demo mode: keeps what would have been sent."""

    def __init__(self, fail=False):
        self.outbox, self.fail = [], fail

    def send(self, messages):
        if self.fail:
            raise MailUnavailable()
        self.outbox.extend(messages)
        return [m[0] for m in messages]


def mailer_from(environ):
    user = (environ.get('NOWCAST_SMTP_USER') or '').strip()
    password = environ.get('NOWCAST_SMTP_PASSWORD') or ''
    return SmtpMailer(user, password) if user and password else None
