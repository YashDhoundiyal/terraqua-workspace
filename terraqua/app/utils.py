from datetime import datetime, timezone


def utcnow():
    """Naive UTC 'now' (matches datetime.utcnow() semantics, but without the
    deprecation warning Python 3.12+ raises for that call)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
