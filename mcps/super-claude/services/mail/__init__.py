"""Mail Service - Email abstraction."""

from .interface import (
    MailAdapter,
    MailAccount,
    Message,
    MessagePage,
    Folder,
    Address,
    Attachment,
    UploadedAttachment,
    MessageFlag,
)
from .manager import MailManager
from .adapters.gmail import GmailAdapter

__all__ = [
    "MailAdapter",
    "MailAccount",
    "Message",
    "MessagePage",
    "Folder",
    "Address",
    "Attachment",
    "UploadedAttachment",
    "MessageFlag",
    "MailManager",
    "GmailAdapter",
]
