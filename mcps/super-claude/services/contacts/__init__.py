"""
Contacts Service

Platform-agnostic contact management.
"""

from .interface import (
    Contact, ContactGroup, ContactPage, ContactsAccount, ContactsAdapter,
    EmailAddress, PhoneNumber, Address, Organization, Name
)
from .manager import ContactsManager

__all__ = [
    "Contact", "ContactGroup", "ContactPage", "ContactsAccount", "ContactsAdapter",
    "EmailAddress", "PhoneNumber", "Address", "Organization", "Name",
    "ContactsManager"
]
