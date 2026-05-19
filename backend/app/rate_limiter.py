"""
Shared rate-limiter instance.

Defined here (not in main.py) to avoid circular imports between
app.main (which imports app.api.jobs) and app.api.jobs (which needs the limiter).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
