"""Airtable API client wrapper using pyairtable."""

from pyairtable import Api
from pyairtable.api.table import Table
from src.config import settings


class AirtableClient:
    """Wrapper for Airtable API providing table access."""

    def __init__(self):
        """Initialize Airtable API client."""
        self.api = Api(settings.airtable_api_key)
        self.base_id = settings.airtable_base_id

    def get_table(self, table_name: str) -> Table:
        """
        Get a table instance from Airtable.

        Args:
            table_name: Name of the table in Airtable

        Returns:
            Table instance for performing operations
        """
        return self.api.table(self.base_id, table_name)


# Global client instance
airtable_client = AirtableClient()
