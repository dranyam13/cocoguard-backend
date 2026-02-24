"""
Timezone utilities for CocoGuard Backend

SQLite's CURRENT_TIMESTAMP / func.now() stores UTC time.
This module provides utilities to convert timestamps to Manila timezone (UTC+8).
"""

from datetime import datetime, timezone, timedelta

# Philippines timezone (UTC+8)
PH_TIMEZONE = timezone(timedelta(hours=8))


def to_manila_time(dt: datetime) -> datetime:
    """Convert datetime from SQLite (UTC) to Manila timezone
    
    Args:
        dt: datetime object (naive or aware)
        
    Returns:
        datetime object in Manila timezone
    """
    if dt is None:
        return None
    # SQLite stores UTC time, so treat naive datetime as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to Manila timezone (UTC+8)
    return dt.astimezone(PH_TIMEZONE)


def to_manila_iso(dt: datetime) -> str:
    """Convert datetime from SQLite (UTC) to Manila timezone ISO string
    
    Args:
        dt: datetime object (naive or aware)
        
    Returns:
        ISO format string with timezone info, e.g., "2026-02-05T10:30:00+08:00"
    """
    manila_dt = to_manila_time(dt)
    if manila_dt is None:
        return None
    return manila_dt.isoformat()


def now_manila() -> datetime:
    """Get current time in Manila timezone"""
    return datetime.now(PH_TIMEZONE)
