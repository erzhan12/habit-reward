"""Base repository with common CRUD operations."""

import logging
from typing import Any
from pyairtable.api.table import Table

from src.airtable.client import airtable_client

# Configure logging
logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, table_name: str):
        """Initialize repository with table name."""
        logger.debug(f"Initializing repository for table: {table_name}")
        self.table: Table = airtable_client.get_table(table_name)

    def _record_to_dict(self, record: dict[str, Any]) -> dict[str, Any]:
        """Convert Airtable record to dict with id."""
        fields = record.get("fields", {})
        fields["id"] = record.get("id")
        return fields
