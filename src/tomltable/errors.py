

class TableJsonMismatchError(ValueError):
    """Raised if spec has more/fewer columns than there are JSONs."""


class TableSpecificationError(ValueError):
    """Raised if TOML table spec has a validation error."""
