import json
import sys
import re

import dataclasses as dcls
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Tuple

import click
import toml


class TableSpecificationError(ValueError):
    pass


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


def load_json_file(filename: str) -> Dict:
    with open(filename, "r") as json_file:
        return json.load(json_file)


def traverse(obj: Any) -> Generator[Tuple[str | None, Any], None, None]:
    if isinstance(obj, dict):
        for key, obj2 in obj.items():
            for subpath, value in traverse(obj2):
                if subpath is None:
                    yield f"{key}", value
                else:
                    yield f"{key}::{subpath}", value
    elif isinstance(obj, list):
        for i, obj2 in enumerate(obj, 1):
            for subpath, value in traverse(obj2):
                if subpath is None:
                    yield f"{i}", value
                else:
                    yield f"{i}::{subpath}", value
    else:
        yield None, obj


def make_json_dict(json_files: List[str]) -> Dict:
    return dict(traverse(json_files))


def add_thousands_separator(string: str) -> str:
    def replace(match: re.Match) -> str:
        number = match.group(2)

        if len(number) < 4:
            return match.group(0)

        for position in range(len(number) - 3, 0, -3):
            number = number[:position] + "," + number[position:]

        return "{}{}".format(match.group(1), number)

    return re.sub(r"(^|[^.0-9])([0-9]+)", replace, string)


def parse_toml_string_field(value: Any,
                            field_name: str,
                            parent_keys: str) -> str:
    if isinstance(value, str):
        return value

    raise TableSpecificationError(
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        + f"a string but it has type '{type(value).__name__}' instead.")


def parse_toml_bool_field(value: Any,
                          field_name: str,
                          parent_keys: str) -> bool:
    if isinstance(value, bool):
        return value

    raise TableSpecificationError(
        f"Value for field '{field_name}' in '{parent_keys}' should be "
        + f"either 'true' or 'false' but it is '{value}' instead.")


def parse_toml_tex_length_field(value: Any,
                                field_name: str,
                                parent_keys: str) -> TeXLength:
    try:
        return TeXLength(value)
    except ValueError as error:
        raise TableSpecificationError(
            f"Value for field '{field_name}' in '{parent_keys}' should "
            + "be a string with a valid TeX length specification but "
            + f"it is '{value}' instead.") from error


def parse_toml_field_cell(value: Any, parent_keys: str) -> List[str]:
    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        if len(value) == 0:
            raise TableSpecificationError(
                f"Value for field 'cell' in '{parent_keys}' should be "
                + "a string or a list of strings but it is an empty "
                + "list instead.")

        if not isinstance(value[0], str):
            # NOTE It is enough to check the type of the first element.
            # `toml.loads` enforces homogeneity within the list.
            #
            raise TableSpecificationError(
                f"Value for field 'cell' in '{parent_keys}' should be "
                + "a string or a list of strings but it is a list of "
                + f"values of type '{type(value[0]).__name__}' "
                + "instead.")

        return value

    raise TableSpecificationError(
        f"Value for field 'cell' in '{parent_keys}' should be a string "
        + "or a list of strings but it has type "
        + f"'{type(value).__name__}' instead.")


def parse_toml_cell_spec(obj: Dict, parent_key: str) -> CellSpec:
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
            raise TableSpecificationError(
                f"Field '{key}' for '{parent_key}.cell' "
                + "is not 'label', 'cell', or 'padding-bottom'.")

    if result.cell is None and result.coef is None:
        raise TableSpecificationError(
            "Must specify either field 'cell' or field 'coef' "
            + f"for '{parent_key}.cell'.")

    if result.cell is not None and result.coef is not None:
        raise TableSpecificationError(
            "Cannot specify both field 'cell' and field 'coef' for "
            + f"'{parent_key}.cell'.")

    return result


def parse_toml_row_spec(obj: Dict, parent_key: str) -> RowSpec:
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
            raise TableSpecificationError(
                f"Field '{key}' for '{parent_key}.row' "
                + "is not 'label', 'cell', or 'padding-bottom'.")

    if cell is None:
        raise TableSpecificationError(
            f"Must specify field 'cell' for '{parent_key}.row'.")

    result.cell = cell

    return result


def parse_toml_header(obj: Dict) -> HeaderSpec:
    result = HeaderSpec()

    for key, value in obj.items():
        if (key in ("cell", "row")
            and (not isinstance(value, list)
                 or any(not isinstance(x, dict) for x in value))):
            raise TableSpecificationError(
                f"Value for 'header.{key}' should be a list "
                + "of dictionaries.")

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
            raise TableSpecificationError(
                "Second-level key for 'header' should be 'cell', "
                + f"'row', or 'add-column-numbers' but it is '{key}' "
                + "instead.")

    return result


def parse_toml_other_section(obj: Dict,
                             parent_key: str) -> OtherSectionSpec:
    result = OtherSectionSpec()

    for key, value in obj.items():
        if (key in ("cell", "row")
            and (not isinstance(value, list)
                 or any(not isinstance(x, dict) for x in value))):
            raise TableSpecificationError(
                f"Value for 'header.{key}' should be a list "
                + "of dictionaries.")

        if key == "cell":
            result.cell_specs = [parse_toml_cell_spec(x, parent_key)
                                 for x in value]
        elif key == "row":
            result.row_specs = [parse_toml_row_spec(x, parent_key)
                                for x in value]
        else:
            raise TableSpecificationError(
                f"Second-level key for '{parent_key}' should be 'cell' "
                + f"or 'row' but it is '{key}' instead.")

    return result


def parse_toml(toml_spec: Dict) -> TableSpec:
    result = TableSpec()

    for key, value in toml_spec.items():
        if key == "header":
            result.header_spec = parse_toml_header(value)
        elif key in ("body", "footer"):
            setattr(result,
                    f"{key}_spec",
                    parse_toml_other_section(value, key))
        else:
            raise TableSpecificationError(
                "Section should be 'header', 'body', or 'footer' "
                + f"but it is '{key}' instead.")

    return result


def confirm_consistent_column_count(
        table_spec: TableSpec,
        json_filenames: List[str]) -> None:
    sections = ("header", "body", "footer")

    def get_and_confirm_counts(section):
        counts_in_section = list(
            len(row.cell)
            for row in (getattr(table_spec, f"{section}_spec")
                        .row_specs)
            if row.cell is not None)

        if (len(counts_in_section) > 1
            and not all(value == counts_in_section[0]
                        for value in counts_in_section)):
            raise TableSpecificationError(
                f"Inconsistent column counts in the {section}: "
                + f"{counts_in_section}.")

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
                raise TableSpecificationError(
                    ("Inconsistent column counts: "
                     + "{} has {} column{} but {} has {}.")
                    .format(section_a,
                            count_a,
                            "s" if count_a > 1 else "",
                            section_b,
                            count_b))

    # Confirm consistency between the specification and the JSON files.
    #

    count_json = len(json_filenames)

    for counts_in_section in counts.values():
        if len(counts_in_section) == 0:
            continue

        count_section = counts_in_section[0]

        if count_json != count_section:
            raise Exception(
                ("Table specification contains {}{} column{} "
                 + "but there {} {}{} JSON file{} passed "
                 + "in the command-line arguments.")
                .format(
                    "only " if count_section < count_json else "",
                    count_section,
                    "s" if count_section > 1 else "",
                    "are" if count_json > 1 else "is",
                    "only " if count_json < count_section else "",
                    count_json,
                    "s" if count_json > 1 else ""))

        break


def get_column_count(table_spec: TableSpec) -> int | None:
    for section in ("header", "body", "footer"):
        row_specs = getattr(table_spec, f"{section}_spec").row_specs

        if len(row_specs) > 0:
            column_count = len(row_specs[0].cell)

            if column_count > 0:
                return column_count

    return None


def escape_tex(value: str) -> str:
    return (value
            .replace("\\", "\\\\")
            .replace("&", "\\&"))


def adapt_cell_value_to_column(value: str, column_number: int) -> str:
    return re.sub(r"%\(n(::[^)]+\)[.0-9]*[dfs])",
                  fr"%({column_number}\1",
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

    if table_spec.header_spec is not None:
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

    if table_spec.body_spec is not None:
        for cell in table_spec.body_spec.cell_specs:
            lines.extend(
                make_rows_for_cell_spec(cell, column_count))

        for row in table_spec.body_spec.row_specs:
            lines.extend(
                make_rows_for_row_spec(row, column_count))

    # Add footer.
    #

    if table_spec.footer_spec is not None:
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


def fill_template(template: str, json_dict: Dict) -> str:
    def replace(match: re.Match) -> str:
        specifier = match.group(0)[len(match.group(1)):]
        key = match.group(2)

        if key not in json_dict:
            raise ValueError(
                f"Specifier '{specifier}' refers to key '{key}' but "
                + "this key is not in the JSON object.")

        try:
            replacement = specifier % json_dict
        except TypeError:
            print("warning: '{}' has the wrong type for specifier '{}'."
                  .format(json_dict[key], specifier),
                  file=sys.stderr)
            return match.group(1)

        return match.group(1) + replacement

    return re.sub(
        r"(^|[^%])%\(([^)]+)\)[-# .0-9]*[dfs]", replace, template)


@click.command(help=("Generate a LaTeX table from a TOML formatted "
                     + "table specification (read from stdin) and "
                     + "a set of JSON files (specified as arguments)."))
@click.option("-j", "--json-filename",
              required=True, type=str, multiple=True,
              help=("JSON file to use as input to the table. "
                    + "In a regression table, each JSON file would "
                    + "most likely correspond to a separate column."))
@click.option("-t", "--title", required=False, type=str,
              help=(r"Add title with the \caption{} command. "
                    + "Implies use of the table and threeparttable "
                    + "environments."))
@click.option("-l", "--label", required=False, type=str,
              help=(r"Add label with the \label{} command. "
                    + "Implies use of the table and threeparttable "
                    + "environments."))
@click.option("-F", "--from-template", is_flag=True,
              help=("Treat stdin as a template instead of a table "
                    + "specification."))
@click.option("-T", "--only-template", is_flag=True,
              help=("Print template instead of the final table to "
                    + "stdout."))
@click.option("-H", "--human-readable-numbers", is_flag=True,
              help=("Add commas as thousands separators to numbers in "
                    + "the final table."))
@click.option("-d", "--debug", is_flag=True)
def main(json_filename, title=None, label=None, from_template=False,
         only_template=False, human_readable_numbers=False,
         debug=False):
    if not debug:
        sys.tracebacklimit = 0

    # Rule out some invalid argument combinations.
    #

    if from_template and only_template:
        raise ValueError(
            "--from-template and --only-template cannot be used "
            + "together.")

    if from_template:
        if title is not None:
            raise ValueError(
                "--from-template and --title cannot be used together.")

        if label is not None:
            raise ValueError(
                "--from-template and --label cannot be used together.")

    if only_template:
        if human_readable_numbers:
            raise ValueError(
                "--only-template and --human-readable-numbers cannot "
                + "be used together.")

    # Load or generate the template.
    #

    if from_template:
        # Read the template from stdin.
        #
        template = sys.stdin.read()
    else:
        # Generate the template from the table specification on stdin.
        #

        table_spec = parse_toml(
            toml.loads(sys.stdin.read()))

        confirm_consistent_column_count(table_spec, json_filename)

        template = make_template(
            table_spec, json_filename, title, label)

    # Use the template.
    #

    if only_template:
        print(template)
    else:
        # Use the template to print the final table.
        #

        json_files = list(load_json_file(filename)
                          for filename in json_filename)

        result = fill_template(template, make_json_dict(json_files))

        if human_readable_numbers:
            result = add_thousands_separator(result)

        print(result)


if __name__ == "__main__":
    main()
