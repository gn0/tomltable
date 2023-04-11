import click
import toml
import json
import sys


class TableSpecificationError(ValueError):
    pass


def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)


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
        # elif index < 0:
        #     raise ValueError(f"Index {index} is invalid.")
        # else:
        #     raise ValueError(
        #         "Object {} has only {} elements.  Index {} is invalid."
        #         .format(obj, len(obj), index))
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
                     + "{} has {} {} but {} has {}.")
                    .format(section_a,
                            count_a,
                            "columns" if count_a > 1 else "column",
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

        if column_count > 1:
            return column_count

    return None


def print_header(table_spec, json_files):
    column_count = get_column_count(table_spec) or len(json_files)

    print(r"\begin{tabular}{lc{%d}}" % column_count)
    print(r"\toprule")

    # TODO Print header.

    print(r"\midrule")


def print_body(table_spec, json_files):
    column_count = get_column_count(table_spec) or len(json_files)

    # TODO Print body.


def print_footer(table_spec, json_files):
    column_count = get_column_count(table_spec) or len(json_files)

    if "footer" in table_spec:
        print(r"\midrule")

        # TODO Print footer.

    print(r"\bottomrule")
    print(r"\end{tabular}")


@click.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-j", "--json-filename",
              required=True, type=str, multiple=True)
def main(json_filename, debug=False):
    if not debug:
        sys.tracebacklimit = 0

    table_spec = toml.loads(sys.stdin.read())

    confirm_consistent_column_count(table_spec, json_filename)

    json_files = list(load_json_file(filename)
                      for filename in json_filename)

    print_header(table_spec, json_files)
    print_body(table_spec, json_files)
    print_footer(table_spec, json_files)


if __name__ == "__main__":
    main()
