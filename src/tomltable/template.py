import sys

import regex

from tomltable.errors import TableSpecificationError
from tomltable.types import CellSpec, RowSpec, TableSpec, TeXLength


def get_column_count(table_spec: TableSpec) -> int | None:
    """Determine the number of columns in a table spec.

    Args:
        table_spec: The validated TableSpec object containing the
            structure.

    Returns:
        int | None: The number of columns if the table contains at least
            one row.  Otherwise None.

    Examples:
        >>> spec = TableSpec()
        >>> get_column_count(spec) is None
        True
        >>> spec.body_spec.row_specs.append(RowSpec(cell=["a", "b"]))
        >>> get_column_count(spec)
        2

    """
    for section in ("header", "body", "footer"):
        row_specs = getattr(table_spec, f"{section}_spec").row_specs

        if len(row_specs) > 0:
            column_count = len(row_specs[0].cell)

            if column_count > 0:
                return column_count

    return None


def escape_tex(value: str) -> str:
    r"""Escape TeX special characters in a string.

    This function handles the ampersand character, which has special
    meaning in TeX for alignment.

    Args:
        value: The string input to be escaped.

    Returns:
        str: The input string with all ampersands replaced by
            backslash-escaped ampersands.

    Examples:
        >>> escape_tex("a & b")
        'a \\& b'
        >>> escape_tex("a and b")
        'a and b'

    """
    return value.replace("&", "\\&")


def adapt_cell_value_to_column(value: str, column_number: int) -> str:
    """Convert a path pattern into a column-specific path.

    This function replaces column index placeholders (`n` in, e.g.,
    `%(n::...)s`) with a specific column index.

    Examples:
        Replacing placeholder with the provided column index:

            >>> adapt_cell_value_to_column("%(n::nobs)d", 2)
            '%(2::nobs)d'

        No placeholder, no replacement:

            >>> adapt_cell_value_to_column("%(1::nobs)d", 2)
            '%(1::nobs)d'

    """
    return regex.sub(
        (
            r"(?V1)(^|[^%])%"
            r"\(n::"
            r"(?P<pat>[^()]*|[^()]*\((?&pat)*\)[^()]*)" # Handle nested
                                                        # parens.
            r"\)"
            r"([-# .0-9]*[dfs])"
        ),
        fr"\1%({column_number}::\2)\3",
        value,
    )


def make_rows_for_cell_spec_custom(
        spec: CellSpec,
        column_count: int) -> list[str]:
    """Generate LaTeX rows for a custom cell spec.

    This function constructs row strings from literal cell values defined
    in the spec, handling labels, separators, line breaks, and vertical
    padding.

    Args:
        spec: The validated CellSpec object containing cell values.
        column_count: The total number of columns in the table.

    Returns:
        list[str]: A list of LaTeX-formatted strings representing rows.

    """
    cell_values = spec.cell or []
    padding_bottom = spec.padding_bottom

    cell_count = len(cell_values)
    rows = []

    for cell_index, cell_value in enumerate(cell_values):
        row = "" if cell_index > 0 else escape_tex(spec.label or "")

        for column_number in range(1, column_count + 1):
            value = adapt_cell_value_to_column(
                cell_value, column_number,
            )

            row += f" & {escape_tex(value)}"

        row += " \\\\"

        if cell_index == cell_count - 1 and padding_bottom is not None:
            row += f"[{padding_bottom}]"

        rows.append(row)

    return rows


def make_rows_for_cell_spec_regression(
        spec: CellSpec,
        column_count: int) -> list[str]:
    """Generate LaTeX rows for a regression-style cell spec.

    This function creates path patterns with placeholders for the column
    index specifically designed to map regression coefficients and
    standard errors to the correct columns dynamically during template
    filling.  It then delegates formatting to the custom row generator.

    Args:
        spec: The validated CellSpec object containing coefficient
            config.
        column_count: The total number of columns in the table.

    Returns:
        list[str]: A list of LaTeX-formatted strings representing rows
            configured for regression data placeholders.

    """
    coef = spec.coef

    cell_values = [
        (
            f"$%(n::coef::{coef}::est).03f$"
            f"%(n::coef::{coef}::stars)s"
        ),
        f"(%(n::coef::{coef}::se).04f)"
    ]

    custom_spec = CellSpec()
    custom_spec.label = spec.label
    custom_spec.cell = cell_values
    custom_spec.padding_bottom = spec.padding_bottom or TeXLength("0.5em")

    return make_rows_for_cell_spec_custom(custom_spec, column_count)


def make_rows_for_cell_spec(
        spec: CellSpec,
        column_count: int) -> list[str]:
    """Generate LaTeX rows based on a cell specification type.

    This function acts as a dispatcher that determines whether to use
    regression-style placeholders or custom literal values based on the
    presence of a 'coef' field in the specification.

    Args:
        spec: The validated CellSpec object to process.
        column_count: The total number of columns in the table.

    Returns:
        list[str]: A list of LaTeX-formatted strings representing rows.

    Raises:
        TableSpecificationError: If neither 'cell' nor 'coef' is
            specified in the input spec (which should be prevented by
            parsing).

    """
    if spec.coef is not None:
        return make_rows_for_cell_spec_regression(spec, column_count)

    if spec.cell is not None:
        return make_rows_for_cell_spec_custom(spec, column_count)

    # NOTE `parse_toml_cell_spec` should ensure that exactly one of
    # 'coef' and 'cell' is specified.  So if we reach here, we have a
    # bug in the parser.
    #
    msg = f"Cell specification {spec} gives neither 'coef' nor 'cell'."
    raise TableSpecificationError(msg)


def make_rows_for_row_spec(
        spec: RowSpec,
        column_count: int) -> list[str]:
    """Generate LaTeX rows for a simple row spec.

    This function constructs row strings from a row label and a fixed
    list of cell values, validating that the number of cells matches the
    table width.

    Args:
        spec: The validated RowSpec object containing rows to format.
        column_count: The total number of columns in the table.

    Returns:
        list[str]: A list of LaTeX-formatted strings representing rows.

    Raises:
        TableSpecificationError: If the number of cells does not match
            the expected column count.

    """
    cell_values = spec.cell
    padding_bottom = spec.padding_bottom

    cell_count = len(cell_values)

    if cell_count != column_count:
        # NOTE `confirm_consistent_column_count` should ensure that the
        # cell count equals the column count.  So if we reach here, we
        # have a bug.
        #
        msg = (
            f"Row specification {spec} has {cell_count} cell values "
            f"but the column count is {column_count}."
        )
        raise TableSpecificationError(msg)

    row = r"{} & {} \\".format(
        escape_tex(spec.label or ""),
        " & ".join(
            escape_tex(value) for value in cell_values
        ),
    )

    if padding_bottom is not None:
        row += f"[{padding_bottom}]"

    return [row]


def make_row_for_column_numbers(column_count: int) -> str:
    r"""Create a LaTeX row that displays column numbers.

    This function generates a row with column numbers, typically used in
    regression tables.

    Args:
        column_count: The total number of columns to label.

    Returns:
        str: A single string representing the formatted LaTeX row.

    Examples:
        >>> make_row_for_column_numbers(3)
        ' & (1) & (2) & (3) \\\\'

    """
    return (
        r" & {} \\"
        .format(" & ".join(f"({number})"
                           for number in range(1, column_count + 1))))


def make_template(
        table_spec: TableSpec,
        json_filenames: list[str],
        title: str | None,
        label: str | None) -> str:
    """Assemble the complete LaTeX table structure from a spec.

    Args:
        table_spec: The validated TableSpec object that describes the
            layout.
        json_filenames: List of paths to JSON files used for getting the
            column count.
        title: Optional caption text for the table.
        label: Optional LaTeX label for referencing the table.

    Returns:
        str: A complete LaTeX string representing the configured table,
            including surrounding environments if applicable.

    """
    column_count = get_column_count(table_spec) or len(json_filenames)
    add_table_env = title is not None or label is not None

    lines = []

    # Add \begin{table} etc. if a title or a label was specified on the
    # command line.
    #
    if add_table_env:
        lines.append(r"\begin{table}[!htb]")
        lines.append(
            r"\begin{adjustbox}{"
            r"max width=\textwidth, "
            r"max height=\textheight, "
            "center"
            "}"
        )
        lines.append(r"\begin{threeparttable}")
        lines.append(r"\centering")
        lines.append(r"\caption{%s}" % (title or ""))

    lines.append(r"\begin{tabular}{l%s}" % ("c" * column_count))
    lines.append(r"\toprule")

    # Add header.
    #

    for cell in table_spec.header_spec.cell_specs:
        lines.extend(
            make_rows_for_cell_spec(cell, column_count))

    for row in table_spec.header_spec.row_specs:
        lines.extend(
            make_rows_for_row_spec(row, column_count))

    if table_spec.header_spec.add_column_numbers:
        lines.append(
            make_row_for_column_numbers(column_count))

    lines.append(r"\midrule")

    # Add body.
    #

    for cell in table_spec.body_spec.cell_specs:
        lines.extend(
            make_rows_for_cell_spec(cell, column_count))

    for row in table_spec.body_spec.row_specs:
        lines.extend(
            make_rows_for_row_spec(row, column_count))

    # Add footer.
    #

    if (len(table_spec.footer_spec.cell_specs) > 0
        or len(table_spec.footer_spec.row_specs) > 0):
        lines.append(r"\midrule")

    for cell in table_spec.footer_spec.cell_specs:
        lines.extend(
            make_rows_for_cell_spec(cell, column_count))

    for row in table_spec.footer_spec.row_specs:
        lines.extend(
            make_rows_for_row_spec(row, column_count))

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    # Add \end{table} etc. if a title or a label was specified on the
    # command line.
    #
    if add_table_env:
        lines.append(r"\label{%s}" % (label or ""))
        lines.append(r"\begin{tablenotes}")
        lines.append(r"\item {\em Notes:}")
        lines.append(r"\end{tablenotes}")
        lines.append(r"\end{threeparttable}")
        lines.append(r"\end{adjustbox}")
        lines.append(r"\end{table}")

    return "\n".join(lines)


def fill_template(
    template: str,
    json_dict: dict,
    *,
    ignore_missing_keys: bool = False,
) -> str:
    """Substitute paths in the template with data from the JSON files.

    Args:
        template: The LaTeX template string.
        json_dict: A dict mapping paths to values.
        ignore_missing_keys: When encountering missing paths, print
            warnings if True, and raise ValueError if False.

    Returns:
        str: The input template with all paths replaced by values from
            `json_dict`.

    Raises:
        ValueError: If a path in the input template is not found in
            `json_dict` and `ignore_missing_keys` is False.

    Examples:
        >>> template = "%(1::name)s is %(1::age)d years old."
        >>> template += " %(2::name)s is %(2::age)d."
        >>> json_dict = {}
        >>> json_dict["1::name"] = "Alice"
        >>> json_dict["1::age"] = 42
        >>> json_dict["2::name"] = "Bob"
        >>> json_dict["2::age"] = 39
        >>> fill_template(template, json_dict)
        'Alice is 42 years old. Bob is 39.'

    """
    def replace(
        match: regex.Match, # ty: ignore[invalid-type-form]
    ) -> str:
        specifier = match.group(0)[len(match.group(1)):]

        # Drop surrounding parentheses.
        #
        key = match.group(2)[1:-1]

        if key not in json_dict:
            msg = (
                f"Specifier '{specifier}' refers to key '{key}' but "
                "this key is not in the JSON object."
            )

            if ignore_missing_keys:
                print(f"warning: {msg}", file=sys.stderr)
                return match.group(1)
            else:
                raise ValueError(msg)

        try:
            replacement = specifier % json_dict
        except TypeError:
            print(
                f"warning: '{json_dict[key]}' has the wrong type "
                f"for specifier '{specifier}'.",
                file=sys.stderr,
            )
            return match.group(1)

        return match.group(1) + replacement

    return regex.sub(
        (
            r"(?V1)(^|[^%])%"
            r"(?P<pat>\([^()]*(?&pat)*[^()]*\))" # Handle nested parens
                                                 # recursively.
            r"[-# .0-9]*[dfs]"
        ),
        replace,
        template,
    )
