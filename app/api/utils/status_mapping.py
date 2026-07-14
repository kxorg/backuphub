"""
Single source of truth for API <-> DB status mapping.
All other modules must import from here to avoid duplication.
"""

API_TO_DB_STATUS = {
    'RUNNING': 'in_progress',
    'SUCCESS': 'success',
    'FAILED': 'error',
}

DB_TO_API_STATUS = {v: k for k, v in API_TO_DB_STATUS.items()}

API_STATUS_CHOICES = list(API_TO_DB_STATUS.keys())