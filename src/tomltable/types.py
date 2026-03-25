import dataclasses as dcls
import re
from dataclasses import dataclass

from typing_extensions import Self


class TeXLength(str):
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
    label: str | None                = None
    cell: list[str] | None           = None
    coef: str | None                 = None
    padding_bottom: TeXLength | None = None


@dataclass
class RowSpec:
    label: str | None                = None
    cell: list[str]                  = dcls.field(default=[])
    padding_bottom: TeXLength | None = None


@dataclass
class OtherSectionSpec:
    cell_specs: list[CellSpec] = dcls.field(default=[])
    row_specs: list[RowSpec]   = dcls.field(default=[])


@dataclass
class HeaderSpec(OtherSectionSpec):
    add_column_numbers: bool   = False


@dataclass
class TableSpec:
    header_spec: HeaderSpec       = dcls.field(default_factory=HeaderSpec)
    body_spec: OtherSectionSpec   = dcls.field(default_factory=OtherSectionSpec)
    footer_spec: OtherSectionSpec = dcls.field(default_factory=OtherSectionSpec)
