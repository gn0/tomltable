import json
import sys
import re

from typing import Any, Dict, Generator, List, Tuple

import click
import toml

from tomltable.parser import confirm_consistent_column_count, parse_toml
from tomltable.template import make_template, fill_template


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
@click.option("-i", "--ignore-missing-keys", is_flag=True,
              help=("Ignore keys that are not present in the "
                    + "corresponding JSON file."))
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
def main(json_filename, title=None, label=None,
         ignore_missing_keys=False, from_template=False,
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
        if ignore_missing_keys:
            raise ValueError(
                "--only-template and --ignore-missing-keys cannot "
                + "be used together.")

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

        result = fill_template(
            template,
            make_json_dict(json_files),
            ignore_missing_keys)

        if human_readable_numbers:
            result = add_thousands_separator(result)

        print(result)


if __name__ == "__main__":
    main()
