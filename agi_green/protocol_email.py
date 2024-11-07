import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
import markdown

from agi_green.dispatcher import Protocol

class EmailProtocol(Protocol):
    '''
    class MyProtocol(Protocol):
        ...
        async def do_something(self, ...):
            ...
            await self.send('email', receiver, subject, content)

        async def on_email_support(self, receiver: str, subject: str, content: str):
            'recieve email to support@example.com'
            ...
    '''
    protocol_id = "email"

    def __init__(self, parent:Protocol):
        super().__init__(parent)

    @staticmethod
    def wrap_email(body: str) -> str:
        return f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                    }}
                </style>
            </head>
            <body>
                {body}
            </body>
        </html>
        """

    @staticmethod
    def md_as_email(md: str, **kwargs) -> str:
        return EmailProtocol.wrap_email(markdown.markdown(md.format(**kwargs)))

    async def do_send(self, sender: str, recipient: str, subject: str, message: str,
                      from_name: str = None, to_name: str = None, **kwargs):
        """
        Asynchronously sends an email to the specified receiver with the given subject and content.

        Content is expected to be in markdown format.
        """
        ecfg = self.config.email._expandvars()
        host = self.dispatcher.server.context.host

        if host is None:
            raise ValueError("Host is not set in the context - cannot send email.")

        if '@' not in sender:
            sender = f"{sender}@{ecfg.domain}"
        # Create a secure SSL context
        ssl_context = ssl.create_default_context()

        # format md
        message = self.md_as_email(message, from_name=from_name, to_name=to_name, host=host, **kwargs)

        if from_name and '<' not in sender:
            sender = f"{from_name} <{sender}>"

        if to_name and '<' not in recipient:
            recipient = f"{to_name} <{recipient}>"

        # Construct the email message
        email_message = MIMEMultipart()
        email_message["From"] = sender
        email_message["To"] = recipient
        email_message["Subject"] = subject
        email_message.attach(MIMEText(message, "html"))

        try:
            # Connect to the SMTP server and send the email asynchronously
            await aiosmtplib.send(
                email_message,
                hostname=ecfg.smtp_server,
                port=ecfg.smtp_port,
                username=sender,
                password=ecfg.smtp_password,
                use_tls=True,
                tls_context=ssl_context
            )
            print("Email sent successfully")
        except Exception as e:
            print(f"Failed to send email: {e}")

