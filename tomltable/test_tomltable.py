import unittest
import re
import io
import contextlib
import toml

import tomltable as m
from tomltable.types import TableSpec


class TestAddThousandsSeparator(unittest.TestCase):
    def test_no_change_to_fractional_part(self):
        text = "foo 0.12345 bar"

        self.assertEqual(text, m.add_thousands_separator(text))

    def test_no_change_to_whole_part_if_fewer_than_four_digits(self):
        text = "foo 1.12345 10.12345 100.12345 bar"

        self.assertEqual(text, m.add_thousands_separator(text))

    def test_commas_added_to_whole_part_if_at_least_four_digits(self):
        text = "foo 1000.12345 10000.12345 100000.12345 1000000.12345 bar"
        expected = ("foo 1,000.12345 10,000.12345 100,000.12345 "
                    + "1,000,000.12345 bar")

        self.assertEqual(expected, m.add_thousands_separator(text))


class TestMakeTemplate(unittest.TestCase):
    def setUp(self):
        self.spec_only_body = toml.loads(
            """
[[body.cell]]
label = "Foo"
coef = "foo"

[[body.cell]]
label = "Bar"
coef = "bar"
"""
        )

        self.spec_body_and_footer_cell = toml.loads(
            """
[[body.cell]]
label = "Foo"
coef = "foo"

[[body.cell]]
label = "Bar"
coef = "bar"

[[footer.cell]]
label = "$N$"
cell = ["%(n::obs)d"]
"""
        )

        self.spec_body_and_footer_row = toml.loads(
            """
[[body.cell]]
label = "Foo"
coef = "foo"

[[body.cell]]
label = "Bar"
coef = "bar"

[[footer.row]]
label = "unit FE"
cell = ["", "YES", "YES"]
"""
        )

        self.spec_without_column_numbers = toml.loads(
            """
[[body.cell]]
label = "Foo"
coef = "foo"
"""
        )

        self.spec_with_column_numbers = toml.loads(
            """
[header]
add-column-numbers = true

[[body.cell]]
label = "Foo"
coef = "foo"
"""
        )

        self.spec_full = toml.loads(
            """
[[header.row]]
cell = ["Lorem", "Ipsum", "Dolor"]

[[header.row]]
cell = ["", "", "Sit Amet"]
padding-bottom = "0.7em"

[[body.cell]]
label = "Foo"
coef = "foo"

[[body.cell]]
label = "Bar"
coef = "bar"

[[footer.cell]]
label = "$N$"
cell = ["%(n::obs)d"]

[[footer.row]]
label = "unit FE"
cell = ["", "YES", "YES"]
"""
        )

        self.spec_full_with_single_column = toml.loads(
            """
[[header.row]]
cell = "Lorem"

[[header.row]]
cell = "Ipsum"

[[body.cell]]
label = "Foo"
coef = "foo"

[[body.cell]]
label = "Bar"
coef = "bar"

[[footer.cell]]
label = "$N$"
cell = "%(n::obs)d"

[[footer.row]]
label = "unit FE"
cell = "YES"
"""
        )

    def test_every_test_spec_is_valid(self):
        for attribute, value in vars(self).items():
            if not attribute.startswith("spec_"):
                continue

            try:
                m.parse_toml(value)
            except:
                self.fail(f"parse_toml fails for {attribute}.")

    def test_only_tabular_if_no_title_and_no_label(self):
        result = m.make_template(
            table_spec=TableSpec(),
            json_filenames=[],
            title=None,
            label=None)

        self.assertEqual(
            ["tabular"],
            re.findall(r"\\begin{([^}]*)}", result))

    def test_only_tabular_only_if_no_title_and_no_label(self):
        for title, label in ((None, "foo"),
                             ("foo", None),
                             ("foo", "bar")):
            result = m.make_template(
                table_spec=TableSpec(),
                json_filenames=[],
                title=title,
                label=label)

            envs_in_result = re.findall(r"\\begin{([^}]*)}", result)

            self.assertIn("tabular", envs_in_result)
            self.assertNotEqual(["tabular"], envs_in_result)

    def test_column_count_matches_table_spec(self):
        def get_column_count(template):
            match = re.search(r"\\begin{tabular}{l(c+)}", template)

            self.assertIsNotNone(match)

            return len(match.group(1))

        self.assertEqual(
            1,
            get_column_count(
                m.make_template(
                    table_spec=m.parse_toml(
                        self.spec_full_with_single_column),
                    json_filenames=["a"],
                    title=None,
                    label=None)))

        for spec in (self.spec_only_body,
                     self.spec_body_and_footer_cell,
                     self.spec_without_column_numbers,
                     self.spec_with_column_numbers):
            self.assertEqual(
                4,
                get_column_count(
                    m.make_template(
                        table_spec=m.parse_toml(spec),
                        json_filenames=["a", "b", "c", "d"],
                        title=None,
                        label=None)))

        for spec in (self.spec_body_and_footer_row,
                     self.spec_full):
            self.assertEqual(
                3,
                get_column_count(
                    m.make_template(
                        table_spec=m.parse_toml(spec),

                        # NOTE In this test, we pass in a specification
                        # for three columns but a list of four JSON
                        # filenames to `make_template`.  These are
                        # inconsistent, and an exception would be raised
                        # by `tomltable.confirm_consistent_column_count`
                        # to prohibit this.  In this test case, however,
                        # we expect the specification to override the
                        # list of JSON filenames.
                        #
                        json_filenames=["a", "b", "c", "d"],

                        title=None,
                        label=None)))

    def test_every_row_has_as_many_cells_as_there_are_columns(self):
        def get_column_count(template):
            match = re.search(r"\\begin{tabular}{l(c+)}", template)

            self.assertIsNotNone(match)

            return len(match.group(1))

        def get_cell_counts(template):
            counts = []
            inside_tabular = False

            for line in template.splitlines():
                if not inside_tabular:
                    if line.startswith("\\begin{tabular}"):
                        inside_tabular = True
                    continue
                elif line == "\\end{tabular}":
                    inside_tabular = False
                    continue
                elif line in ("\\toprule", "\\midrule", "\\bottomrule"):
                    continue

                counts.append(line.count("&"))

            return counts

        for (spec, json_filenames) in (
                (self.spec_only_body, ["a", "b", "c"]),
                (self.spec_body_and_footer_cell, ["a", "b", "c"]),
                (self.spec_body_and_footer_row, ["a", "b", "c"]),
                (self.spec_without_column_numbers, ["a", "b", "c"]),
                (self.spec_with_column_numbers, ["a", "b", "c"]),
                (self.spec_full, ["a", "b", "c"]),
                (self.spec_full_with_single_column, ["a"])):
            template = m.make_template(
                table_spec=m.parse_toml(spec),
                json_filenames=json_filenames,
                title=None,
                label=None)

            column_count = get_column_count(template)
            cell_counts = get_cell_counts(template)

            self.assertTrue(all(x == column_count for x in cell_counts))

    def test_column_numbers_in_header_if_specified(self):
        template = m.make_template(
            table_spec=m.parse_toml(self.spec_with_column_numbers),
            json_filenames=["a", "b", "c"],
            title=None,
            label=None)

        self.assertEqual(
            1,
            len([line
                 for line in template.splitlines()
                 if re.match(r"^ *& *\(1\) *& *\(2\) *& *\(3\) *\\\\$",
                             line) is not None]))

    def test_no_column_numbers_in_header_if_unspecified(self):
        template = m.make_template(
            table_spec=m.parse_toml(self.spec_without_column_numbers),
            json_filenames=["a", "b", "c"],
            title=None,
            label=None)

        self.assertTrue(
            all(re.match(r"^ *& *\(1\)", line) is None
                for line in template.splitlines()))


class TestFillTemplate(unittest.TestCase):
    def setUp(self):
        self.json_dict = {
            "foo": "bar",
            "bar::baz": 3.14,
            "foo::(bar)::baz": 2.72,
            "baz": None,
        }

    def test_no_change_without_conversion_specifiers(self):
        template = "lorem ipsum dolor sit amet consectetuer"

        self.assertEqual(
            template, m.fill_template(template, self.json_dict))

    def test_no_change_with_escaped_conversion_specifier(self):
        template = "lorem %%(foo)s dolor %%(sit)s amet consectetuer"

        self.assertEqual(
            template, m.fill_template(template, self.json_dict))

    def test_string_conversion_specifiers(self):
        template = "lorem %(foo)s dolor %(bar::baz)s amet %(baz)s"
        expected = "lorem bar dolor 3.14 amet None"

        self.assertEqual(
            expected, m.fill_template(template, self.json_dict))

    def test_integer_conversion_specifiers(self):
        template = "lorem %(foo)d dolor %(bar::baz)d amet %(baz)d"
        expected = "lorem  dolor 3 amet "

        output = io.StringIO()

        with contextlib.redirect_stderr(output):
            result = m.fill_template(template, self.json_dict)

        # Inserts empty string on TypeError.
        #
        self.assertEqual(expected, result)

        # Prints warning for each conversion error.
        #
        self.assertEqual(
            2,
            len(re.findall("^warning: ",
                           output.getvalue(),
                           flags=re.MULTILINE)))

    def test_float_conversion_specifiers(self):
        template = "lorem %(foo)f dolor %(bar::baz)f amet %(baz)f"
        expected = "lorem  dolor 3.140000 amet "

        output = io.StringIO()

        with contextlib.redirect_stderr(output):
            result = m.fill_template(template, self.json_dict)

        # Inserts empty string on TypeError.
        #
        self.assertEqual(expected, result)

        # Prints warning for each conversion error.
        #
        self.assertEqual(
            2,
            len(re.findall("^warning: ",
                           output.getvalue(),
                           flags=re.MULTILINE)))

    def test_float_conversion_specifiers_with_flags(self):
        template = ("lorem %(foo).03f dolor %(bar::baz).03f amet "
                    + "%(baz).03f")
        expected = "lorem  dolor 3.140 amet "

        output = io.StringIO()

        with contextlib.redirect_stderr(output):
            result = m.fill_template(template, self.json_dict)

        # Inserts empty string on TypeError.
        #
        self.assertEqual(expected, result)

        # Prints warning for each conversion error.
        #
        self.assertEqual(
            2,
            len(re.findall("^warning: ",
                           output.getvalue(),
                           flags=re.MULTILINE)))

    def test_key_that_includes_parentheses(self):
        template = "lorem ipsum %(foo::(bar)::baz).03f amet"
        expected = "lorem ipsum 2.720 amet"

        self.assertEqual(
            expected, m.fill_template(template, self.json_dict))

    def test_key_that_includes_parentheses_inside_parentheses(self):
        template = "lorem ipsum (%(foo::(bar)::baz).03f) amet"
        expected = "lorem ipsum (2.720) amet"

        self.assertEqual(
            expected, m.fill_template(template, self.json_dict))

    def test_raises_exception_for_missing_key(self):
        template = "lorem %(ipsum)s dolor sit amet"

        with self.assertRaises(ValueError):
            m.fill_template(template, self.json_dict)
