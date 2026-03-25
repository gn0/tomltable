from typing import Any, Literal

from tomltable.errors import TableSpecificationError
from tomltable.types import (
    CellSpec,
    HeaderSpec,
    OtherSectionSpec,
    RowSpec,
    TableSpec,
    TeXLength,
)


def parse_toml_string_field(
    value: Any,
    field_name: str,
    parent_keys: str,
) -> str:
    """Validate that a value is a string and return it.

    This function ensures that a configuration field contains a string
    value as expected for TOML specifications.  If the type does not
    match, a validation error is raised.

    Args:
        value: The raw value to validate.
        field_name: The name of the field being validated.
        parent_keys: A string describing the path to this field in the
            spec.

    Returns:
        str: The input value if it is a string.

    Raises:
        TableSpecificationError: If the value is not a string.

    """
    if isinstance(value, str):
        return value

    msg = (
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        f"a string but it has type '{type(value).__name__}' instead."
    )
    raise TableSpecificationError(msg)


def parse_toml_bool_field(
    value: Any,
    field_name: str,
    parent_keys: str,
) -> bool:
    """Validate that a value is a boolean and return it.

    This function ensures that a configuration field contains a boolean
    value (True or False). If the type does not match, a validation
    error is raised.

    Args:
        value: The raw value to validate.
        field_name: The name of the field being validated.
        parent_keys: A string describing the path to this field in the
            spec.

    Returns:
        bool: The input value if it is a boolean.

    Raises:
        TableSpecificationError: If the value is not a boolean.

    """
    if isinstance(value, bool):
        return value

    msg = (
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        f"either 'true' or 'false' but it is '{value}' instead."
    )
    raise TableSpecificationError(msg)


def parse_toml_tex_length_field(
    value: Any,
    field_name: str,
    parent_keys: str,
) -> TeXLength:
    """Validate that a value is a valid TeX length specification.

    This function parses the input to ensure it represents a valid TeX
    unit length (e.g., '10pt', '1cm') and returns a TeXLength object.

    Args:
        value: The raw value to validate.
        field_name: The name of the field being validated.
        parent_keys: A string describing the path to this field in the
            spec.

    Returns:
        TeXLength: An object representing the validated length.

    Raises:
        TableSpecificationError: If the value is not a valid TeX length
            string.

    """
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
    """Parse the value of a 'cell' field into a list of strings.

    This function ensures that the input value is either a string or a
    non-empty list of strings.  If the input value is a string, then
    that value is returned as a singleton list.

    Args:
        value: The raw value to parse (string or list).
        parent_keys: A string describing the path to this field in the
            spec.

    Returns:
        list[str]: A non-empty list of strings extracted from the input.

    Raises:
        TableSpecificationError: If the value is not a string, empty
            list, or contains non-string elements.

    Examples:
        >>> parse_toml_field_cell("a", "foobar")
        ['a']
        >>> parse_toml_field_cell(["a", "b"], "foobar")
        ['a', 'b']

    """
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
    """Parse a dict into a structured CellSpec object.

    This function validates the structure of a cell definition within a
    table specification.  It ensures that either 'cell' or 'coef' is
    specified, but not both.  Supported keys include 'label', 'cell',
    'padding-bottom', and 'coef'.

    Args:
        obj: Dict containing cell specifications.
        parent_key: Key describing the section context (e.g., "header").

    Returns:
        CellSpec: A validated and structured CellSpec instance.

    Raises:
        TableSpecificationError: If required fields are missing, invalid
            keys are used, or if both 'cell' and 'coef' are specified.

    Examples:
        >>> obj = {"cell": "a", "label": "x"}
        >>> spec = parse_toml_cell_spec(obj, "foobar")
        >>> spec.label
        'x'
        >>> spec.cell
        ['a']

    """
    result = CellSpec()

    for key, value in obj.items():
        if key in ("label", "coef"):
            setattr(
                result,
                key,
                parse_toml_string_field(
                    value, key, f"{parent_key}.cell",
                ),
            )
        elif key == "cell":
            result.cell = parse_toml_field_cell(
                value, f"{parent_key}.cell",
            )
        elif key == "padding-bottom":
            result.padding_bottom = parse_toml_tex_length_field(
                value, key, f"{parent_key}.cell",
            )
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
    """Parse a dict into a structured RowSpec object.

    This function validates the structure of a row definition.  A 'cell'
    field is mandatory for all rows.  Supported keys include 'label',
    'cell', and 'padding-bottom'.

    Args:
        obj: Dict containing row specifications.
        parent_key: Key describing the section context (e.g., "body").

    Returns:
        RowSpec: A validated and structured RowSpec instance.

    Raises:
        TableSpecificationError: If required fields are missing or
            invalid keys are used.

    Examples:
        >>> obj = {"cell": ["a", "b"], "label": "x"}
        >>> spec = parse_toml_row_spec(obj, "foobar")
        >>> spec.label
        'x'
        >>> spec.cell
        ['a', 'b']

    """
    result = RowSpec()
    cell = None

    for key, value in obj.items():
        if key == "label":
            result.label = parse_toml_string_field(
                value, key, f"{parent_key}.row",
            )
        elif key == "cell":
            cell = parse_toml_field_cell(value, f"{parent_key}.row")
        elif key == "padding-bottom":
            result.padding_bottom = parse_toml_tex_length_field(
                value, key, f"{parent_key}.row",
            )
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
    """Parse a dict into a structured HeaderSpec object.

    This function handles the 'header' section of the table
    specification.  It expects lists of dicts for 'cell' and 'row' keys,
    and an optional boolean flag for 'add-column-numbers'.

    Args:
        obj: Dict containing header specifications.

    Returns:
        HeaderSpec: A validated and structured HeaderSpec instance.

    Raises:
        TableSpecificationError: If the structure does not match
            expectations or invalid keys are provided.

    Examples:
        >>> spec = parse_toml_header({"add-column-numbers": True})
        >>> spec.add_column_numbers
        True

    """
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
                value, key, "header",
            )
        elif key == "cell":
            result.cell_specs = [
                parse_toml_cell_spec(x, "header") for x in value
            ]
        elif key == "row":
            result.row_specs = [
                parse_toml_row_spec(x, "header") for x in value
            ]
        else:
            msg = (
                "Second-level key for 'header' should be 'cell', "
                f"'row', or 'add-column-numbers' but it is '{key}' "
                "instead."
            )
            raise TableSpecificationError(msg)

    return result


def parse_toml_other_section(
    obj: dict,
    parent_key: str,
) -> OtherSectionSpec:
    """Parse a dict into a structured OtherSectionSpec object.

    This function handles the 'body' and 'footer' sections of the table
    specification.  It validates that 'cell' and 'row' keys contain
    lists of dict with valid content.

    Args:
        obj: Dict containing section specifications.
        parent_key: The name of the section (e.g., "body" or "footer").

    Returns:
        OtherSectionSpec: A validated and structured OtherSectionSpec
            instance.

    Raises:
        TableSpecificationError: If the structure does not match
            expectations.

    """
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
            result.cell_specs = [
                parse_toml_cell_spec(x, parent_key) for x in value
            ]
        elif key == "row":
            result.row_specs = [
                parse_toml_row_spec(x, parent_key) for x in value
            ]
        else:
            msg = (
                f"Second-level key for '{parent_key}' should be 'cell' "
                f"or 'row' but it is '{key}' instead."
            )
            raise TableSpecificationError(msg)

    return result


def parse_toml(toml_spec: dict) -> TableSpec:
    """Parse the entire table specification dict into a structured spec.

    This function aggregates the header, body, and footer specifications
    into a single `TableSpec` object.  Each section must be named
    correctly, and its content validated by corresponding helper
    functions.

    Args:
        toml_spec: The full TOML specification as a dict.

    Returns:
        TableSpec: A complete and validated table specification object.

    Raises:
        TableSpecificationError: If any section name is invalid or
            contains structural errors that cannot be parsed.

    """
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
    json_filenames: list[str],
) -> None:
    """Verify that column counts are consistent throughout table spec.

    This function ensures three things:

    1. All rows in the header section have the same number of cells.
    2. The header column count matches the body and footer row counts.
    3. The specification's column count matches the number of JSON files
       provided (where each file represents one column).

    Args:
        table_spec: The validated TableSpec to check.
        json_filenames: List of paths to JSON data files.

    Returns:
        None: Function raises an error on failure instead of returning a
            value.

    Raises:
        TableSpecificationError: If internal row counts differ across
            rows or sections, or if the total column count does not
            match JSON inputs.
        Exception: If the spec column count doesn't match the number of
            JSON files.

    """
    sections = ("header", "body", "footer")

    def get_and_confirm_counts(
        section: Literal["header", "body", "footer"],
    ) -> list[int]:
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
