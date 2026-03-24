import re

from typing import List
import dataclasses as dcls
from dataclasses import dataclass


class TeXLength(str):
    def __new__(cls, value: str):
        if (not isinstance(value, str)
            or re.match(
                "^(-?[0-9]*[.])?[0-9]+(pt|mm|cm|in|ex|em|mu|sp)$",
                value) is None):
            raise ValueError(
                f"'{value}' is not a valid TeX length specification.")

        return super().__new__(cls, value)


@dataclass
class CellSpec:
    label: str | None                = None
    cell: List[str] | None           = None
    coef: str | None                 = None
    padding_bottom: TeXLength | None = None


@dataclass
class RowSpec:
    label: str | None                = None
    cell: List[str]                  = dcls.field(default_factory=lambda: [])
    padding_bottom: TeXLength | None = None


@dataclass
class OtherSectionSpec:
    cell_specs: List[CellSpec] = dcls.field(default_factory=lambda: [])
    row_specs: List[RowSpec]   = dcls.field(default_factory=lambda: [])


@dataclass
class HeaderSpec(OtherSectionSpec):
    add_column_numbers: bool   = False


@dataclass
class TableSpec:
    header_spec: HeaderSpec       = dcls.field(default_factory=lambda: HeaderSpec())
    body_spec: OtherSectionSpec   = dcls.field(default_factory=lambda: OtherSectionSpec())
    footer_spec: OtherSectionSpec = dcls.field(default_factory=lambda: OtherSectionSpec())
