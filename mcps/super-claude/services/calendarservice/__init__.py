"""Calendar Service - Calendar event abstraction."""

from .interface import (
    CalendarAdapter,
    CalendarAccount,
    Event,
    EventPage,
    Calendar,
    Attendee,
    TimeSlot,
    FreeBusyResult,
    Reminder,
    EventStatus,
    ResponseStatus,
    Visibility,
)
from .manager import CalendarManager
from .adapters.gcal import GCalAdapter

__all__ = [
    "CalendarAdapter",
    "CalendarAccount",
    "Event",
    "EventPage",
    "Calendar",
    "Attendee",
    "TimeSlot",
    "FreeBusyResult",
    "Reminder",
    "EventStatus",
    "ResponseStatus",
    "Visibility",
    "CalendarManager",
    "GCalAdapter",
]
