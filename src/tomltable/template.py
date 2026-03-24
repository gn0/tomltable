import sys
import regex

from typing import Dict, List

from tomltable.errors import TableSpecificationError
from tomltable.types import TeXLength, CellSpec, RowSpec, TableSpec


def get_column_count(table_spec: TableSpec) -> int | None:
    for section in ("header", "body", "footer"):
        row_specs = getattr(table_spec, f"{section}_spec").row_specs

        if len(row_specs) > 0:
            column_count = len(row_specs[0].cell)

            if column_count > 0:
                return column_count

    return None


def escape_tex(value: str) -> str:
    return value.replace("&", "\\&")


def adapt_cell_value_to_column(value: str, column_number: int) -> str:
    return regex.sub(
        (r"(?V1)(^|[^%])%"
         + r"\(n::"
         + r"(?P<pat>[^()]*|[^()]*\((?&pat)*\)[^()]*)" # Handle nested
                                                       # parens.
         + r"\)"
         + r"([-# .0-9]*[dfs])"),
        fr"\1%({column_number}::\2)\3",
        value)


def make_rows_for_cell_spec_custom(
        spec: CellSpec,
        column_count: int) -> List[str]:
    cell_values = spec.cell or []
    padding_bottom = spec.padding_bottom

    cell_count = len(cell_values)
    rows = []

    for cell_index, cell_value in enumerate(cell_values):
        if cell_index == 0:
            row = escape_tex(spec.label or "")
        else:
            row = ""

        for column_number in range(1, column_count + 1):
            value = adapt_cell_value_to_column(
                cell_value, column_number)

            row += " & {}".format(escape_tex(value))

        row += " \\\\"

        if cell_index == cell_count - 1 and padding_bottom is not None:
            row += f"[{padding_bottom}]"

        rows.append(row)

    return rows


def make_rows_for_cell_spec_regression(
        spec: CellSpec,
        column_count: int) -> List[str]:
    coef = spec.coef

    cell_values = [
        (f"$%(n::coef::{coef}::est).03f$"
         + f"%(n::coef::{coef}::stars)s"),
        f"(%(n::coef::{coef}::se).04f)"
    ]

    custom_spec = CellSpec()
    custom_spec.label = spec.label
    custom_spec.cell = cell_values
    custom_spec.padding_bottom = spec.padding_bottom or TeXLength("0.5em")

    return make_rows_for_cell_spec_custom(custom_spec, column_count)


def make_rows_for_cell_spec(
        spec: CellSpec,
        column_count: int) -> List[str]:
    if spec.coef is not None:
        return make_rows_for_cell_spec_regression(spec, column_count)

    if spec.cell is not None:
        return make_rows_for_cell_spec_custom(spec, column_count)

    # NOTE `parse_toml_cell_spec` should ensure that exactly one of
    # 'coef' and 'cell' is specified.  So if we reach here, we have a
    # bug in the parser.
    #
    raise TableSpecificationError(
        f"Cell specification {spec} gives neither 'coef' nor 'cell'.")


def make_rows_for_row_spec(
        spec: RowSpec,
        column_count: int) -> List[str]:
    cell_values = spec.cell
    padding_bottom = spec.padding_bottom

    cell_count = len(cell_values)

    if cell_count != column_count:
        # NOTE `confirm_consistent_column_count` should ensure that the
        # cell count equals the column count.  So if we reach here, we
        # have a bug.
        #
        raise TableSpecificationError(
            f"Row specification {spec} has {cell_count} cell values "
            + f"but the column count is {column_count}.")

    row = (r"{} & {} \\"
           .format(escape_tex(spec.label or ""),
                   " & ".join(escape_tex(value)
                              for value in cell_values)))

    if padding_bottom is not None:
        row += f"[{padding_bottom}]"

    return [row]


def make_row_for_column_numbers(column_count: int) -> str:
    return (
        r" & {} \\"
        .format(" & ".join(f"({number})"
                           for number in range(1, column_count + 1))))


def make_template(
        table_spec: TableSpec,
        json_filenames: List[str],
        title: str | None,
        label: str | None) -> str:
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
            + r"max width=\textwidth, "
            + r"max height=\textheight, "
            + "center}")
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


def fill_template(template: str,
                  json_dict: Dict,
                  ignore_missing_keys: bool = False) -> str:
    def replace(match: regex.Match) -> str:
        specifier = match.group(0)[len(match.group(1)):]

        # Drop surrounding parentheses.
        #
        key = match.group(2)[1:-1]

        if key not in json_dict:
            message = (f"Specifier '{specifier}' refers to key '{key}' "
                       + "but this key is not in the JSON object.")

            if ignore_missing_keys:
                print(f"warning: {message}", file=sys.stderr)
                return match.group(1)
            else:
                raise ValueError(message)

        try:
            replacement = specifier % json_dict
        except TypeError:
            print((f"warning: '{json_dict[key]}' has the wrong type "
                   + f"for specifier '{specifier}'."),
                  file=sys.stderr)
            return match.group(1)

        return match.group(1) + replacement

    return regex.sub(
        (r"(?V1)(^|[^%])%"
         + r"(?P<pat>\([^()]*(?&pat)*[^()]*\))" # Handle nested parens
                                                # recursively.
         + r"[-# .0-9]*[dfs]"),
        replace,
        template)
