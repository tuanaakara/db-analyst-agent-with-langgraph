"""
Utility functions for the AI Analyst project.

This module contains small, reusable helper functions that are used across
different parts of the application.
"""
import sqlite3


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Args:
        db_path (str): The file path to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(db_path)
