"""
Mail Service Interface

Core abstraction for email providers. Adapters implement this interface
to provide email functionality for Gmail, Outlook, IMAP, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class MessageFlag(Enum):
    """Standard message flags."""
    READ = "read"
    UNREAD = "unread"
    STARRED = "starred"
    IMPORTANT = "important"
    DRAFT = "draft"
    SENT = "sent"
    TRASH = "trash"
    SPAM = "spam"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Address:
    """Email address with optional display name."""
    email: str
    name: Optional[str] = None
    
    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class Attachment:
    """Email attachment metadata (from received message)."""
    id: str              # Provider-specific ID for downloading
    filename: str
    mime_type: str
    size: int


@dataclass
class UploadedAttachment:
    """Result of uploading an attachment for sending."""
    id: str              # Provider-specific ID to reference in send()
    filename: str
    mime_type: str
    size: int


@dataclass
class Message:
    """Email message."""
    id: str
    thread_id: Optional[str]          # Provider's thread identifier (for grouping)
    subject: str
    sender: Address
    recipients: List[Address]
    cc: List[Address] = field(default_factory=list)
    bcc: List[Address] = field(default_factory=list)
    date: Optional[datetime] = None   # Timezone-aware UTC datetime
    snippet: str = ""                 # Preview text
    body_text: Optional[str] = None   # Plain text body (loaded on get_message)
    body_html: Optional[str] = None   # HTML body (loaded on get_message)
    flags: List[MessageFlag] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)  # Provider-specific labels/folders
    attachments: List[Attachment] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass 
class Folder:
    """Mailbox folder."""
    id: str
    name: str
    path: str                         # Full path like "INBOX/Receipts"
    message_count: int = 0
    unread_count: int = 0
    folder_type: Optional[str] = None # inbox, sent, drafts, trash, spam, custom


@dataclass
class MessagePage:
    """Paginated message results."""
    messages: List[Message]
    next_cursor: Optional[str] = None   # None means no more pages
    total_estimate: Optional[int] = None  # Some providers give approximate count


@dataclass
class MailAccount:
    """A named mail account configuration."""
    name: str             # User-defined label: "work", "personal"
    adapter: str          # Adapter type: "gmail", "outlook", "imap"
    credentials_ref: str  # 1Password reference
    config: Dict[str, Any] = field(default_factory=dict)  # Adapter-specific config


# =============================================================================
# Adapter Interface
# =============================================================================

class MailAdapter(ABC):
    """
    Base class for mail adapters.
    
    Each adapter (Gmail, Outlook, IMAP) implements this interface.
    All datetime values are timezone-aware UTC.
    """
    
    adapter_type: str = "base"  # Override in subclass: "gmail", "outlook", "imap"
    
    def __init__(self, account: MailAccount):
        """
        Initialize adapter with account config.
        
        Args:
            account: MailAccount with credentials and config
        """
        self.account = account
        self._client = None
    
    # =========================================================================
    # Connection
    # =========================================================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to mail service.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to mail service."""
        pass
    
    # =========================================================================
    # Folder Operations
    # =========================================================================
    
    @abstractmethod
    async def list_folders(self) -> List[Folder]:
        """
        List all mailbox folders.
        
        Returns:
            List of Folder objects
        """
        pass
    
    # =========================================================================
    # Message Listing / Reading
    # =========================================================================
    
    @abstractmethod
    async def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        cursor: Optional[str] = None,
        unread_only: bool = False
    ) -> MessagePage:
        """
        List messages in folder with cursor-based pagination.
        
        Returns Message objects with metadata but NOT full body.
        Use get_message() to retrieve full content.
        
        Args:
            folder: Folder name or ID
            limit: Maximum messages to return (1-100)
            cursor: Pagination cursor from previous MessagePage.next_cursor
            unread_only: Filter to unread messages only
        
        Returns:
            MessagePage with messages and optional next_cursor
        """
        pass
    
    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Get full message including body content.
        
        Args:
            message_id: Message identifier
        
        Returns:
            Message with body_text/body_html populated, or None if not found
        """
        pass
    
    @abstractmethod
    async def list_thread(self, thread_id: str) -> List[Message]:
        """
        Get all messages in a thread, ordered chronologically.
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            List of Messages in the thread (oldest first)
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        folder: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> MessagePage:
        """
        Search messages.
        
        Query format is adapter-specific:
        - Gmail: Uses Gmail search syntax (from:, to:, subject:, has:attachment, etc.)
        - IMAP: Basic text search
        - Outlook: KQL syntax
        
        Args:
            query: Search query string
            folder: Optional folder to search within
            limit: Maximum results to return
            cursor: Pagination cursor
        
        Returns:
            MessagePage with matching messages
        """
        pass
    
    # =========================================================================
    # Attachments
    # =========================================================================
    
    @abstractmethod
    async def upload_attachment(
        self,
        local_path: str,
        filename: Optional[str] = None
    ) -> UploadedAttachment:
        """
        Upload attachment for use in send/reply/forward.
        
        Args:
            local_path: Path to local file
            filename: Override filename (defaults to basename of local_path)
        
        Returns:
            UploadedAttachment with ID to reference in send operations
        """
        pass
    
    @abstractmethod
    async def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        local_path: str
    ) -> str:
        """
        Download attachment from a received message.
        
        Args:
            message_id: Message containing the attachment
            attachment_id: Attachment identifier from Message.attachments
            local_path: Local path to save file
        
        Returns:
            Success message or error
        """
        pass
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    @abstractmethod
    async def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False,
        attachment_ids: Optional[List[str]] = None
    ) -> str:
        """
        Send new message.
        
        Args:
            to: List of recipient email addresses
            subject: Message subject
            body: Message body (plain text or HTML based on html flag)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            html: If True, body is HTML; if False, plain text
            attachment_ids: IDs from upload_attachment()
        
        Returns:
            Sent message ID or error message
        """
        pass
    
    @abstractmethod
    async def reply(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False,
        attachment_ids: Optional[List[str]] = None
    ) -> str:
        """
        Reply to a message. Automatically handles threading.
        
        Args:
            message_id: Message to reply to
            body: Reply body
            reply_all: If True, reply to all recipients
            html: If True, body is HTML
            attachment_ids: IDs from upload_attachment()
        
        Returns:
            Sent message ID or error message
        """
        pass
    
    @abstractmethod
    async def forward(
        self,
        message_id: str,
        to: List[str],
        body: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None
    ) -> str:
        """
        Forward a message. Original attachments are included automatically.
        
        Args:
            message_id: Message to forward
            to: Forward recipients
            body: Optional additional text to prepend
            attachment_ids: Additional attachments from upload_attachment()
        
        Returns:
            Sent message ID or error message
        """
        pass
    
    # =========================================================================
    # Organization
    # =========================================================================
    
    @abstractmethod
    async def move(self, message_id: str, folder: str) -> str:
        """
        Move message to a folder.
        
        Args:
            message_id: Message to move
            folder: Destination folder name or ID
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def delete(self, message_id: str, permanent: bool = False) -> str:
        """
        Delete a message.
        
        Args:
            message_id: Message to delete
            permanent: If True, permanently delete; if False, move to trash
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def mark_read(self, message_id: str, read: bool = True) -> str:
        """
        Mark message as read or unread.
        
        Args:
            message_id: Message to update
            read: True to mark read, False to mark unread
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def mark_flagged(self, message_id: str, flagged: bool = True) -> str:
        """
        Mark message as starred/flagged or remove flag.
        
        Args:
            message_id: Message to update
            flagged: True to add star/flag, False to remove
        
        Returns:
            Success message or error
        """
        pass
