from typing import Any

from tomltable.errors import TableSpecificationError
from tomltable.types import (
    CellSpec,
    HeaderSpec,
    OtherSectionSpec,
    RowSpec,
    TableSpec,
    TeXLength,
)


def parse_toml_string_field(value: Any,
                            field_name: str,
                            parent_keys: str) -> str:
    if isinstance(value, str):
        return value

    msg = (
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        f"a string but it has type '{type(value).__name__}' instead."
    )
    raise TableSpecificationError(msg)


def parse_toml_bool_field(value: Any,
                          field_name: str,
                          parent_keys: str) -> bool:
    if isinstance(value, bool):
        return value

    msg = (
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        f"either 'true' or 'false' but it is '{value}' instead."
    )
    raise TableSpecificationError(msg)


def parse_toml_tex_length_field(value: Any,
                                field_name: str,
                                parent_keys: str) -> TeXLength:
    try:
        return TeXLength(value)
    except ValueError as error:
        msg = (
            f"Value for field '{field_name}' in '{parent_keys}' should "
            "be a string with a valid TeX length specification but it "
            f"is '{value}' instead."
        )
        raise TableSpecificationError(msg) from error


def parse_toml_field_cell(value: Any, parent_keys: str) -> list[str]:
    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        if len(value) == 0:
            msg = (
                f"Value for field 'cell' in '{parent_keys}' should be "
                "a string or a list of strings but it is an empty list "
                "instead."
            )
            raise TableSpecificationError(msg)

        if not isinstance(value[0], str):
            # NOTE It is enough to check the type of the first element.
            # `toml.loads` enforces homogeneity within the list.
            #
            msg = (
                f"Value for field 'cell' in '{parent_keys}' should be "
                "a string or a list of strings but it is a list of "
                f"values of type '{type(value[0]).__name__}' instead."
            )
            raise TableSpecificationError(msg)

        return value

    msg = (
        f"Value for field 'cell' in '{parent_keys}' should be a string "
        "or a list of strings but it has type "
        f"'{type(value).__name__}' instead."
    )
    raise TableSpecificationError(msg)


def parse_toml_cell_spec(obj: dict, parent_key: str) -> CellSpec:
    result = CellSpec()

    for key, value in obj.items():
        if key in ("label", "coef"):
            setattr(result,
                    key,
                    parse_toml_string_field(
                        value, key, f"{parent_key}.cell"))
        elif key == "cell":
            result.cell = parse_toml_field_cell(
                value, f"{parent_key}.cell")
        elif key == "padding-bottom":
            result.padding_bottom = parse_toml_tex_length_field(
                value, key, f"{parent_key}.cell")
        else:
            msg = (
                f"Field '{key}' for '{parent_key}.cell' is not "
                "'label', 'cell', or 'padding-bottom'."
            )
            raise TableSpecificationError(msg)

    if result.cell is None and result.coef is None:
        msg = (
            "Must specify either field 'cell' or field 'coef' for "
            f"'{parent_key}.cell'."
        )
        raise TableSpecificationError(msg)

    if result.cell is not None and result.coef is not None:
        msg = (
            "Cannot specify both field 'cell' and field 'coef' for "
            f"'{parent_key}.cell'."
        )
        raise TableSpecificationError(msg)

    return result


def parse_toml_row_spec(obj: dict, parent_key: str) -> RowSpec:
    result = RowSpec()
    cell = None

    for key, value in obj.items():
        if key == "label":
            result.label = parse_toml_string_field(
                value, key, f"{parent_key}.row")
        elif key == "cell":
            cell = parse_toml_field_cell(value, f"{parent_key}.row")
        elif key == "padding-bottom":
            result.padding_bottom = parse_toml_tex_length_field(
                value, key, f"{parent_key}.row")
        else:
            msg = (
                f"Field '{key}' for '{parent_key}.row' is not 'label', "
                "'cell', or 'padding-bottom'."
            )
            raise TableSpecificationError(msg)

    if cell is None:
        msg = f"Must specify field 'cell' for '{parent_key}.row'."
        raise TableSpecificationError(msg)

    result.cell = cell

    return result


def parse_toml_header(obj: dict) -> HeaderSpec:
    result = HeaderSpec()

    for key, value in obj.items():
        if (key in ("cell", "row")
            and (not isinstance(value, list)
                 or any(not isinstance(x, dict) for x in value))):
            msg = (
                f"Value for 'header.{key}' should be a list of "
                "dictionaries."
            )
            raise TableSpecificationError(msg)

        if key == "add-column-numbers":
            result.add_column_numbers = parse_toml_bool_field(
                value, key, "header")
        elif key == "cell":
            result.cell_specs = [parse_toml_cell_spec(x, "header")
                                 for x in value]
        elif key == "row":
            result.row_specs = [parse_toml_row_spec(x, "header")
                                for x in value]
        else:
            msg = (
                "Second-level key for 'header' should be 'cell', "
                f"'row', or 'add-column-numbers' but it is '{key}' "
                "instead."
            )
            raise TableSpecificationError(msg)

    return result


def parse_toml_other_section(obj: dict,
                             parent_key: str) -> OtherSectionSpec:
    result = OtherSectionSpec()

    for key, value in obj.items():
        if (key in ("cell", "row")
            and (not isinstance(value, list)
                 or any(not isinstance(x, dict) for x in value))):
            msg = (
                f"Value for 'header.{key}' should be a list of "
                "dictionaries."
            )
            raise TableSpecificationError(msg)

        if key == "cell":
            result.cell_specs = [parse_toml_cell_spec(x, parent_key)
                                 for x in value]
        elif key == "row":
            result.row_specs = [parse_toml_row_spec(x, parent_key)
                                for x in value]
        else:
            msg = (
                f"Second-level key for '{parent_key}' should be 'cell' "
                f"or 'row' but it is '{key}' instead."
            )
            raise TableSpecificationError(msg)

    return result


def parse_toml(toml_spec: dict) -> TableSpec:
    result = TableSpec()

    for key, value in toml_spec.items():
        if key == "header":
            result.header_spec = parse_toml_header(value)
        elif key in ("body", "footer"):
            setattr(result,
                    f"{key}_spec",
                    parse_toml_other_section(value, key))
        else:
            msg = (
                "Section should be 'header', 'body', or 'footer' but "
                f"it is '{key}' instead."
            )
            raise TableSpecificationError(msg)

    return result


def confirm_consistent_column_count(
        table_spec: TableSpec,
        json_filenames: list[str]) -> None:
    sections = ("header", "body", "footer")

    def get_and_confirm_counts(section):
        counts_in_section = [
            len(row.cell)
            for row in (
                getattr(table_spec, f"{section}_spec")
                .row_specs
            )
            if row.cell is not None
        ]

        if (len(counts_in_section) > 1
            and not all(value == counts_in_section[0]
                        for value in counts_in_section)):
            msg = (
                f"Inconsistent column counts in the {section}: "
                f"{counts_in_section}."
            )
            raise TableSpecificationError(msg)

        return counts_in_section

    # Confirm consistency within section.
    #
    counts = {section: get_and_confirm_counts(section)
              for section in sections}

    # Confirm consistency across sections.
    #
    for index, section_a in enumerate(sections):
        if len(counts[section_a]) == 0:
            continue

        count_a = counts[section_a][0]

        for section_b in sections[index + 1:]:
            if len(counts[section_b]) == 0:
                continue

            count_b = counts[section_b][0]

            if count_a != count_b:
                msg = (
                    f"Inconsistent column counts: {count_a} in "
                    f"{section_a} but {count_b} in {section_b}."
                )
                raise TableSpecificationError(msg)

    # Confirm consistency between the specification and the JSON files.
    #

    count_json = len(json_filenames)

    for counts_in_section in counts.values():
        if len(counts_in_section) == 0:
            continue

        count_section = counts_in_section[0]

        if count_json != count_section:
            plural_section = "s" if count_section > 1 else ""
            plural_json = "s" if count_json > 1 else ""

            msg = (
                "Inconsistency between the table specification and the "
                f"command-line arguments: {count_section} "
                f"column{plural_section} in the specification but "
                f"{count_json} JSON file{plural_json} in the arguments."
            )
            raise Exception(msg)

        break
