import click
import toml
import json
import sys
import re


class TableSpecificationError(ValueError):
    pass


def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)


def traverse(obj):
    if type(obj) is dict:
        for key, obj2 in obj.items():
            for subpath, value in traverse(obj2):
                if subpath is None:
                    yield "%s" % key, value
                else:
                    yield "%s::%s" % (key, subpath), value
    elif type(obj) is list:
        for i, obj2 in enumerate(obj, 1):
            for subpath, value in traverse(obj2):
                if subpath is None:
                    yield "%d" % i, value
                else:
                    yield "%d::%s" % (i, subpath), value
    else:
        yield None, obj


def make_json_dict(json_files):
    return dict(traverse(json_files))


def add_thousands_separator(string):
    def replace(match):
        number = match.group(2)

        if len(number) < 4:
            return match.group(0)

        for position in range(len(number) - 3, 0, -3):
            number = number[:position] + "," + number[position:]

        return "{}{}".format(match.group(1), number)

    return re.sub(r"(^|[^.0-9])([0-9]+)", replace, string)


def nested_get(obj, *args):
    if len(args) == 0:
        return obj
    elif type(obj) is list:
        index = args[0]

        if type(index) is not int:
            raise ValueError(
                "Non-numeric index '{}' for object {}."
                .format(index, obj))
        elif 0 <= index < len(obj):
            return nested_get(obj[index], *args[1:])
        else:
            return dict()
    elif type(obj) is dict:
        key = args[0]

        if key in obj:
            return nested_get(obj[key], *args[1:])
        else:
            return dict()
    else:
        raise ValueError(f"Object {obj} is not a list or a dict.")


def confirm_consistent_column_count(table_spec, json_filenames):
    sections = ("header", "body", "footer")

    def get_and_confirm_counts(section):
        counts_in_section = list(
            len(row["cell"])
            for row in nested_get(
                    table_spec, section, "row")
            if "cell" in row)

        if (len(counts_in_section) > 1
            and not all(value == counts_in_section[0]
                        for value in counts_in_section)):
            raise TableSpecificationError(
                "Inconsistent column counts in the {}: {}."
                .format(section,
                        counts_in_section))

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


def get_column_count(table_spec):
    for section in ("header", "body", "footer"):
        column_count = len(
            nested_get(table_spec, section, "row", 0, "cell"))

        if column_count > 0:
            return column_count

    return None


def escape_tex(value):
    return (value
            .replace("\\", "\\\\")
            .replace("&", "\\&"))


def adapt_cell_value_to_column(value, column_number):
    return re.sub(r"%\(n(::[^)]+\)[.0-9]*[dfs])",
                  r"%({}\1".format(column_number),
                  value)


def make_rows_for_column_spec_custom(spec, column_count):
    cell_values = spec.get("cell", [])
    padding_bottom = spec.get("padding-bottom")

    cell_count = len(cell_values)
    rows = []

    for cell_index, cell_value in enumerate(cell_values):
        if cell_index == 0:
            row = escape_tex(spec.get("label", ""))
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


def make_rows_for_column_spec_regression(spec, column_count):
    coef = spec.get("coef")

    cell_values = [
        ("$%(n::coef::{0}::est).03f$"
         + "%(n::coef::{0}::stars)s").format(coef),
        "(%(n::coef::{0}::se).04f)".format(coef)
    ]

    custom_spec = {
        "label": spec.get("label", ""),
        "cell": cell_values,
        "padding-bottom": "1em"
    }

    return make_rows_for_column_spec_custom(custom_spec, column_count)


def make_rows_for_column_spec(spec, column_count):
    if "coef" in spec:
        return make_rows_for_column_spec_regression(spec, column_count)
    elif "cell" in spec:
        return make_rows_for_column_spec_custom(spec, column_count)
    else:
        raise TableSpecificationError(
            "Column specification {} gives neither 'coef' nor 'cell'."
            .format(spec))


def make_rows_for_row_spec(spec, column_count):
    cell_values = spec.get("cell", [])
    padding_bottom = spec.get("padding-bottom")

    cell_count = len(cell_values)

    if cell_count != column_count:
        raise TableSpecificationError(
            ("Row specification {} has {} cell values but the column "
             + "count is {}.")
            .format(spec,
                    cell_count,
                    column_count))

    row = (r"{} & {} \\"
           .format(escape_tex(spec.get("label", "")),
                   " & ".join(escape_tex(value)
                              for value in cell_values)))

    if padding_bottom is not None:
        row += f"[{padding_bottom}]"

    return [row]


def make_template(table_spec, json_filenames, title, label):
    column_count = get_column_count(table_spec) or len(json_filenames)
    add_table_env = title is not None or label is not None

    lines = []

    # Add \begin{table} etc. if a title or a label was specified on the
    # command line.
    #
    if add_table_env:
        lines.append(r"\begin{table}[!htb]")
        lines.append(r"\begin{threeparttable}")
        lines.append(r"\centering")
        lines.append(r"\caption{%s}" % (title or ""))

    lines.append(r"\begin{tabular}{lc{%d}}" % column_count)
    lines.append(r"\toprule")

    # Add header.
    #

    for column in nested_get(table_spec, "header", "column"):
        lines.extend(
            make_rows_for_column_spec(column, column_count))

    for row in nested_get(table_spec, "header", "row"):
        lines.extend(
            make_rows_for_row_spec(row, column_count))

    lines.append(r"\midrule")

    # Add body.
    #

    for column in nested_get(table_spec, "body", "column"):
        lines.extend(
            make_rows_for_column_spec(column, column_count))

    for row in nested_get(table_spec, "body", "row"):
        lines.extend(
            make_rows_for_row_spec(row, column_count))

    # Add footer.
    #

    if "footer" in table_spec:
        lines.append(r"\midrule")

        for column in nested_get(table_spec, "footer", "column"):
            lines.extend(
                make_rows_for_column_spec(column, column_count))

        for row in nested_get(table_spec, "footer", "row"):
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
        lines.append(r"\end{table}")

    return "\n".join(lines)


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

    if from_template:
        # Read the template from stdin.
        #
        template = sys.stdin.read()
    else:
        # Generate the template from the table specification on stdin.
        #

        table_spec = toml.loads(sys.stdin.read())

        confirm_consistent_column_count(table_spec, json_filename)

        template = make_template(
            table_spec, json_filename, title, label)

    if only_template:
        print(template)
    else:
        # Use the template to print the final table.
        #

        json_files = list(load_json_file(filename)
                        for filename in json_filename)

        result = template % make_json_dict(json_files)

        if human_readable_numbers:
            result = add_thousands_separator(result)

        print(result)


if __name__ == "__main__":
    main()
