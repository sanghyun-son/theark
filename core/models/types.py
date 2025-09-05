"""Type aliases for the application."""

from typing import Literal

# Database ID types
PaperID = int
ArxivID = str
Language = str

# Query ordering types
PriorityOrder = Literal["summary_status", "updated_at"]
