"""Paper source enumeration."""

from enum import Enum


class PaperSource(Enum):
    """Paper source enumeration."""

    ARXIV = "arxiv"
    PUBMED = "pubmed"
    IEEE = "ieee"
    CUSTOM = "custom"

    @property
    def default_categories(self) -> list[str]:
        """Get default categories for this source."""
        defaults = {
            PaperSource.ARXIV: ["cs.OTHER"],
            PaperSource.PUBMED: ["med.OTHER"],
            PaperSource.IEEE: ["eng.OTHER"],
            PaperSource.CUSTOM: ["gen.OTHER"],
        }
        return defaults.get(self, ["gen.OTHER"])

    @property
    def default_category(self) -> str:
        """Get default primary category for this source."""
        return self.default_categories[0]
