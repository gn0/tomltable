import dataclasses as dcls
import re
from dataclasses import dataclass

from typing_extensions import Self


class TeXLength(str):
    """A valid TeX length specification.

    A string subclass that ensures values conform to valid TeX length
    unit formats (e.g., '10pt', '1cm', '2.5ex').  Attempts with invalid
    formats raise a ValueError during instantiation.

    Valid unit suffixes are: pt, mm, cm, in, ex, em, mu, sp.

    Attributes:
        value: The validated string representation stored as the
            underlying string content.

    Example:
        Create a valid TeXLength instance:

            >>> from tomltable.types import TeXLength
            >>> length = TeXLength("10pt")
            >>> str(length)
            '10pt'

        Negative and decimal values are supported:

            >>> TeXLength("-2.5em")
            '-2.5em'
            >>> TeXLength("0.5cm")
            '0.5cm'

        An invalid unit raises a ValueError:

            >>> TeXLength("5hr")
            Traceback (most recent call last):
            ...
            ValueError: '5hr' is not a valid TeX length specification.

    """

    __slots__ = ()

    def __new__(cls, value: str) -> Self:
        if (not isinstance(value, str)
            or re.match(
                "^(-?[0-9]*[.])?[0-9]+(pt|mm|cm|in|ex|em|mu|sp)$",
                value) is None):
            msg = f"'{value}' is not a valid TeX length specification."
            raise ValueError(msg)

        return super().__new__(cls, value)


@dataclass
class CellSpec:
    """Specification for custom table cell or a regression coefficient.

    Attributes:
        label: Optional text label for the cell, shown in the first
            column on the row.
        cell: List of custom string values to display in the table cell.
        coef: Coefficient name for regression-style cells.
        padding_bottom: Optional vertical spacing below the row (e.g.,
            "0.5em").

    """

    label: str | None                = None
    cell: list[str] | None           = None
    coef: str | None                 = None
    padding_bottom: TeXLength | None = None


@dataclass
class RowSpec:
    """Specification for a table row containing multiple cells.

    This dataclass represents a complete row in a LaTeX table, combining
    a label with a fixed list of cell values.  Used when generating
    table rows from TOML specifications where all column values are
    known at specification time.

    Attributes:
        label: Optional text label for the row (e.g., "Firm fixed
            effects").
        cell: List of string values for each column in this row. Must
            match the total column count of the table (e.g., ["", "YES",
            "YES"]).
        padding_bottom: Optional vertical spacing below the row (e.g.,
            "0.5em").

    """

    label: str | None                = None
    cell: list[str]                  = dcls.field(default_factory=lambda: [])  # noqa: PIE807
    padding_bottom: TeXLength | None = None


@dataclass
class OtherSectionSpec:
    """Base specification for table sections containing cells and rows.

    This class represents the body or footer sections of a LaTeX table,
    containing definitions for how cells should be populated and
    arranged.

    Attributes:
        cell_specs: List of CellSpec objects defining coefficient-based
            or custom cells in this section.
        row_specs: List of RowSpec objects defining complete rows in
            this section.

    """

    cell_specs: list[CellSpec] = dcls.field(default_factory=lambda: [])  # noqa: PIE807
    row_specs: list[RowSpec]   = dcls.field(default_factory=lambda: [])  # noqa: PIE807


@dataclass
class HeaderSpec(OtherSectionSpec):
    r"""Specification for table header section.

    This class extends `OtherSectionSpec` to add support for displaying
    column numbers (e.g., `(1)`, `(2)`) below the column labels, which
    is common in regression tables.

    Attributes:
        add_column_numbers: When True, adds a row with column numbers
            before the `\midrule` that is placed between the header and
            the body section.
        cell_specs: List of CellSpec objects for header cells.
        row_specs: List of RowSpec objects for header rows.

    """

    add_column_numbers: bool   = False


@dataclass
class TableSpec:
    """Complete specification for a LaTeX table including all sections.

    This class represents the parsed TOML specification and contains
    definitions for header, body, and footer sections that together
    form a complete LaTeX table structure.

    Attributes:
        header_spec: A HeaderSpec object that represents the header
            section.
        body_spec: An OtherSectionSpec object that represents the body
            section, typically containing regression coefficients.
        footer_spec: An OtherSectionSpec object that represents the
            footer section, typically containing additional information
            like observation counts.

    """

    header_spec: HeaderSpec       = dcls.field(default_factory=HeaderSpec)
    body_spec: OtherSectionSpec   = dcls.field(default_factory=OtherSectionSpec)
    footer_spec: OtherSectionSpec = dcls.field(default_factory=OtherSectionSpec)
