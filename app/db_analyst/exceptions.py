"""
Custom exception classes for the AI Analyst project.

These exceptions are used to handle specific error conditions in a structured way,
such as problems with initialization or database connectivity.
"""

class InitializationError(Exception):
    """Raised when there is an error during the agent's initialization process."""
    pass

class DatabaseConnectionError(InitializationError):
    """Raised specifically when the database file cannot be found or connected to."""
    pass