"""
Calendar Service Interface

Core abstraction for calendar providers. Adapters implement this interface
to provide calendar functionality for Google Calendar, Outlook, CalDAV, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class EventStatus(Enum):
    """Event confirmation status."""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ResponseStatus(Enum):
    """Attendee response status."""
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needs_action"


class Visibility(Enum):
    """Event visibility."""
    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Attendee:
    """Event attendee."""
    email: str
    name: Optional[str] = None
    response: ResponseStatus = ResponseStatus.NEEDS_ACTION
    optional: bool = False
    organizer: bool = False
    self_: bool = False  # Is this the current user?


@dataclass
class Reminder:
    """Event reminder."""
    minutes_before: int
    method: str = "popup"  # popup, email, sms (provider-dependent)


@dataclass
class Event:
    """Calendar event."""
    id: str
    calendar_id: str
    title: str
    start: datetime                    # Timezone-aware UTC datetime
    end: datetime                      # Timezone-aware UTC datetime
    all_day: bool = False
    description: Optional[str] = None
    location: Optional[str] = None
    status: EventStatus = EventStatus.CONFIRMED
    visibility: Visibility = Visibility.DEFAULT
    busy: bool = True                  # Show as busy (vs free/available)
    
    # People
    organizer: Optional[str] = None    # Organizer email
    attendees: List[Attendee] = field(default_factory=list)
    
    # Recurrence
    recurrence: Optional[str] = None   # RRULE string if this is a recurring event
    recurring_event_id: Optional[str] = None  # Parent event ID if this is an instance
    
    # Reminders
    reminders: List[Reminder] = field(default_factory=list)
    use_default_reminders: bool = True
    
    # Links
    conference_link: Optional[str] = None  # Meet/Zoom/Teams link
    html_link: Optional[str] = None        # Web link to view event
    
    # Metadata
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    etag: Optional[str] = None             # For conflict detection on updates


@dataclass
class Calendar:
    """A calendar (container for events)."""
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None        # Hex color code
    primary: bool = False              # Is this the user's primary calendar?
    writable: bool = True              # Can we create/modify events?
    owner: Optional[str] = None        # Owner email
    timezone: Optional[str] = None     # IANA timezone (e.g., "America/New_York")


@dataclass
class TimeSlot:
    """A time slot (for free/busy queries)."""
    start: datetime                    # Timezone-aware UTC
    end: datetime                      # Timezone-aware UTC


@dataclass
class FreeBusyResult:
    """Result of a free/busy query."""
    calendar_id: str
    busy_slots: List[TimeSlot]         # When the calendar is busy
    

@dataclass
class EventPage:
    """Paginated event results."""
    events: List[Event]
    next_cursor: Optional[str] = None  # None means no more pages


@dataclass
class CalendarAccount:
    """A named calendar account configuration."""
    name: str             # User-defined label: "work", "personal"
    adapter: str          # Adapter type: "gcal", "outlook", "caldav"
    credentials_ref: str  # 1Password reference
    config: Dict[str, Any] = field(default_factory=dict)  # Adapter-specific config


# =============================================================================
# Adapter Interface
# =============================================================================

class CalendarAdapter(ABC):
    """
    Base class for calendar adapters.
    
    Each adapter (GCal, Outlook, CalDAV) implements this interface.
    All datetime values are timezone-aware UTC.
    """
    
    adapter_type: str = "base"  # Override in subclass: "gcal", "outlook", "caldav"
    
    def __init__(self, account: CalendarAccount):
        """
        Initialize adapter with account config.
        
        Args:
            account: CalendarAccount with credentials and config
        """
        self.account = account
        self._client = None
    
    # =========================================================================
    # Connection
    # =========================================================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to calendar service.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to calendar service."""
        pass
    
    # =========================================================================
    # Calendar Operations
    # =========================================================================
    
    @abstractmethod
    async def list_calendars(self) -> List[Calendar]:
        """
        List all accessible calendars.
        
        Returns:
            List of Calendar objects
        """
        pass
    
    @abstractmethod
    async def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        """
        Get calendar details by ID.
        
        Args:
            calendar_id: Calendar identifier (use "primary" for default)
        
        Returns:
            Calendar or None if not found
        """
        pass
    
    # =========================================================================
    # Event Listing
    # =========================================================================
    
    @abstractmethod
    async def list_events(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> EventPage:
        """
        List events in date range with cursor-based pagination.
        
        Args:
            calendar_id: Calendar to query (use "primary" for default)
            start: Range start (timezone-aware UTC)
            end: Range end (timezone-aware UTC)
            limit: Maximum events to return (1-250)
            cursor: Pagination cursor from previous EventPage.next_cursor
        
        Returns:
            EventPage with events and optional next_cursor
        """
        pass
    
    @abstractmethod
    async def get_event(self, calendar_id: str, event_id: str) -> Optional[Event]:
        """
        Get full event details.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Event identifier
        
        Returns:
            Event or None if not found
        """
        pass
    
    @abstractmethod
    async def search_events(
        self,
        query: str,
        calendar_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> EventPage:
        """
        Search events by text.
        
        Searches title, description, location, and attendees.
        
        Args:
            query: Search text
            calendar_id: Optional calendar to search (None = all calendars)
            start: Optional range start
            end: Optional range end
            limit: Maximum results
            cursor: Pagination cursor
        
        Returns:
            EventPage with matching events
        """
        pass
    
    # =========================================================================
    # Recurring Event Operations
    # =========================================================================
    
    @abstractmethod
    async def list_event_instances(
        self,
        calendar_id: str,
        event_id: str,
        start: datetime,
        end: datetime,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> EventPage:
        """
        Get instances of a recurring event in date range.
        
        Args:
            calendar_id: Calendar containing the recurring event
            event_id: Recurring event identifier
            start: Range start (timezone-aware UTC)
            end: Range end (timezone-aware UTC)
            limit: Maximum instances to return
            cursor: Pagination cursor
        
        Returns:
            EventPage with event instances
        """
        pass
    
    # =========================================================================
    # Event CRUD
    # =========================================================================
    
    @abstractmethod
    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start: datetime,
        end: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[Reminder]] = None,
        all_day: bool = False,
        recurrence: Optional[str] = None,
        visibility: Visibility = Visibility.DEFAULT,
        conference: bool = False
    ) -> str:
        """
        Create a new event.
        
        Args:
            calendar_id: Calendar to create event in
            title: Event title/summary
            start: Start time (timezone-aware UTC, or date for all-day)
            end: End time (timezone-aware UTC, or date for all-day)
            description: Optional event description
            location: Optional location
            attendees: Optional list of attendee email addresses
            reminders: Optional reminders (overrides default if provided)
            all_day: If True, start/end are dates, not datetimes
            recurrence: Optional RRULE string for recurring events
            visibility: Event visibility
            conference: If True, create a conference link (Meet/Teams)
        
        Returns:
            Created event ID or error message
        """
        pass
    
    @abstractmethod
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[Reminder]] = None,
        visibility: Optional[Visibility] = None
    ) -> str:
        """
        Update an existing event. Only provided fields are changed.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Event to update
            title: New title (None = keep existing)
            start: New start time
            end: New end time
            description: New description
            location: New location
            attendees: New attendee list (replaces existing)
            reminders: New reminders (replaces existing)
            visibility: New visibility
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def update_event_instance(
        self,
        calendar_id: str,
        event_id: str,
        instance_id: str,
        title: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> str:
        """
        Update a single instance of a recurring event.
        
        Creates an exception to the recurrence rule.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Recurring event ID
            instance_id: Specific instance ID (from list_event_instances)
            title: New title for this instance
            start: New start time for this instance
            end: New end time for this instance
            description: New description for this instance
            location: New location for this instance
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def delete_event(self, calendar_id: str, event_id: str) -> str:
        """
        Delete an event.
        
        For recurring events, deletes all instances.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Event to delete
        
        Returns:
            Success message or error
        """
        pass
    
    @abstractmethod
    async def delete_event_instance(
        self,
        calendar_id: str,
        event_id: str,
        instance_id: str
    ) -> str:
        """
        Delete a single instance of a recurring event.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Recurring event ID
            instance_id: Specific instance ID to delete
        
        Returns:
            Success message or error
        """
        pass
    
    # =========================================================================
    # Availability
    # =========================================================================
    
    @abstractmethod
    async def get_free_busy(
        self,
        calendar_ids: List[str],
        start: datetime,
        end: datetime
    ) -> List[FreeBusyResult]:
        """
        Get free/busy information for calendars.
        
        Args:
            calendar_ids: Calendars to check
            start: Range start (timezone-aware UTC)
            end: Range end (timezone-aware UTC)
        
        Returns:
            List of FreeBusyResult with busy slots for each calendar
        """
        pass
    
    async def find_free_slots(
        self,
        calendar_ids: List[str],
        start: datetime,
        end: datetime,
        duration: timedelta,
        working_hours: Optional[tuple] = None
    ) -> List[TimeSlot]:
        """
        Find available time slots across calendars.
        
        Default implementation uses get_free_busy. Override for efficiency.
        
        Args:
            calendar_ids: Calendars to check
            start: Range start
            end: Range end
            duration: Required slot duration
            working_hours: Optional (start_hour, end_hour) to limit search
                          e.g., (9, 17) for 9 AM - 5 PM
        
        Returns:
            List of available TimeSlots that fit the duration
        """
        # Default implementation - adapters can override for better performance
        free_busy = await self.get_free_busy(calendar_ids, start, end)
        
        # Merge all busy slots
        all_busy: List[TimeSlot] = []
        for fb in free_busy:
            all_busy.extend(fb.busy_slots)
        
        # Sort by start time
        all_busy.sort(key=lambda s: s.start)
        
        # Find gaps that fit duration
        free_slots: List[TimeSlot] = []
        current = start
        
        for busy in all_busy:
            if busy.start > current:
                gap = busy.start - current
                if gap >= duration:
                    slot_end = busy.start
                    # Apply working hours filter if specified
                    if working_hours:
                        # This is simplified - real impl would handle day boundaries
                        pass
                    free_slots.append(TimeSlot(start=current, end=slot_end))
            current = max(current, busy.end)
        
        # Check final gap
        if end > current and (end - current) >= duration:
            free_slots.append(TimeSlot(start=current, end=end))
        
        return free_slots
    
    # =========================================================================
    # Attendee Response
    # =========================================================================
    
    async def respond_to_event(
        self,
        calendar_id: str,
        event_id: str,
        response: ResponseStatus,
        comment: Optional[str] = None
    ) -> str:
        """
        Respond to an event invitation.
        
        Args:
            calendar_id: Calendar containing the event
            event_id: Event to respond to
            response: Your response (accepted, declined, tentative)
            comment: Optional comment with response
        
        Returns:
            Success message or error
        """
        return "❌ Event responses not supported by this adapter"
