import json
import re
import sys
from collections.abc import Generator
from typing import Any

import click
import toml

from tomltable.parser import confirm_consistent_column_count, parse_toml
from tomltable.template import fill_template, make_template


def load_json_file(filename: str) -> dict:
    with open(filename, "r") as json_file:
        return json.load(json_file)


def traverse(obj: Any) -> Generator[tuple[str | None, Any], None, None]:
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


def make_json_dict(json_files: list[dict]) -> dict:
    return dict(traverse(json_files))


def add_thousands_separator(string: str) -> str:
    def replace(match: re.Match) -> str:
        number = match.group(2)

        if len(number) < 4:
            return match.group(0)

        for position in range(len(number) - 3, 0, -3):
            number = number[:position] + "," + number[position:]

        return f"{match.group(1)}{number}"

    return re.sub(r"(^|[^.0-9])([0-9]+)", replace, string)


@click.command(help=(
    "Generate a LaTeX table from a TOML formatted table specification "
    "(read from stdin) and a set of JSON files (specified as "
    "arguments)."
))
@click.option("-j", "--json-filename",
              required=True, type=str, multiple=True,
              help=(
                  "JSON file to use as input to the table. In a "
                  "regression table, each JSON file would most likely "
                  "correspond to a separate column."
              ))
@click.option("-t", "--title", required=False, type=str,
              help=(
                  r"Add title with the \caption{} command. Implies use "
                  "of the table and threeparttable environments."
              ))
@click.option("-l", "--label", required=False, type=str,
              help=(
                  r"Add label with the \label{} command. Implies use "
                  "of the table and threeparttable environments."
              ))
@click.option("-i", "--ignore-missing-keys", is_flag=True,
              help=(
                  "Ignore keys that are not present in the "
                  "corresponding JSON file."
              ))
@click.option("-F", "--from-template", is_flag=True,
              help=(
                  "Treat stdin as a template instead of a table "
                  "specification."
              ))
@click.option("-T", "--only-template", is_flag=True,
              help=(
                  "Print template instead of the final table to stdout."
              ))
@click.option("-H", "--human-readable-numbers", is_flag=True,
              help=(
                  "Add commas as thousands separators to numbers in "
                  "the final table."
              ))
@click.option("-d", "--debug", is_flag=True)
def main(
    json_filename: str,
    title: str | None,
    label: str | None,
    *,
    ignore_missing_keys: bool = False,
    from_template: bool = False,
    only_template: bool = False,
    human_readable_numbers: bool = False,
    debug: bool = False,
) -> None:
    if not debug:
        sys.tracebacklimit = 0

    # Rule out some invalid argument combinations.
    #

    if from_template and only_template:
        msg = (
            "--from-template and --only-template cannot be used "
            "together."
        )
        raise ValueError(msg)

    if from_template:
        if title is not None:
            msg = "--from-template and --title cannot be used together."
            raise ValueError(msg)

        if label is not None:
            msg = "--from-template and --label cannot be used together."
            raise ValueError(msg)

    if only_template:
        if ignore_missing_keys:
            msg = (
                "--only-template and --ignore-missing-keys cannot be "
                "used together."
            )
            raise ValueError(msg)

        if human_readable_numbers:
            msg = (
                "--only-template and --human-readable-numbers cannot "
                "be used together."
            )
            raise ValueError(msg)

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

        confirm_consistent_column_count(table_spec, [json_filename])

        template = make_template(
            table_spec, [json_filename], title, label)

    # Use the template.
    #

    if only_template:
        print(template, end="")
    else:
        # Use the template to print the final table.
        #

        json_files = [
            load_json_file(filename) for filename in json_filename
        ]

        result = fill_template(
            template,
            make_json_dict(json_files),
            ignore_missing_keys=ignore_missing_keys)

        if human_readable_numbers:
            result = add_thousands_separator(result)

        print(result, end="")


if __name__ == "__main__":
    main()
