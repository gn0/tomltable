import unittest
import toml
import re

from tomltable import tomltable as m


class TestNestedGet(unittest.TestCase):
    def test_existing_levels_with_dict_only(self):
        obj_level_1 = {"a": 1, "b": 2}
        obj_level_2 = {"a": {"c": 1, "d": 2}, "b": 3}
        obj_level_3 = {"a": {"c": {"e": 1, "f": 2}, "d": 3}, "b": 4}

        self.assertEqual(1, m.nested_get(obj_level_1, "a"))
        self.assertEqual(2, m.nested_get(obj_level_2, "a", "d"))
        self.assertEqual(1, m.nested_get(obj_level_3, "a", "c", "e"))

    def test_existing_levels_with_list_only(self):
        obj_level_1 = [1, 2]
        obj_level_2 = [[1, 2], 3]
        obj_level_3 = [[[1, 2], 3], 4]

        self.assertEqual(1, m.nested_get(obj_level_1, 0))
        self.assertEqual(2, m.nested_get(obj_level_2, 0, 1))
        self.assertEqual(1, m.nested_get(obj_level_3, 0, 0, 0))

    def test_existing_levels_with_both_dict_and_list(self):
        obj = {"a": [{"b": 1}, {"b": 2}, {"b": 3}], "c": 4}

        self.assertEqual(1, m.nested_get(obj, "a", 0, "b"))
        self.assertEqual(2, m.nested_get(obj, "a", 1, "b"))

    def test_missing_level_with_dict_only(self):
        obj_level_1 = {"a": 1, "b": 2}
        obj_level_2 = {"a": {"c": 1, "d": 2}, "b": 3}
        obj_level_3 = {"a": {"c": {"e": 1, "f": 2}, "d": 3}, "b": 4}

        self.assertEqual(dict(), m.nested_get(obj_level_1, "c"))

        self.assertEqual(dict(), m.nested_get(obj_level_2, "c"))
        self.assertEqual(dict(), m.nested_get(obj_level_2, "a", "e"))

        self.assertEqual(dict(), m.nested_get(obj_level_3, "c"))
        self.assertEqual(dict(), m.nested_get(obj_level_3, "a", "e"))
        self.assertEqual(dict(), m.nested_get(obj_level_3, "a", "c", "g"))

    def test_missing_level_with_list_only(self):
        obj_level_1 = [1, 2]
        obj_level_2 = [[1, 2], 3]
        obj_level_3 = [[[1, 2], 3], 4]

        self.assertEqual(dict(), m.nested_get(obj_level_1, 2))

        self.assertEqual(dict(), m.nested_get(obj_level_2, 2))
        self.assertEqual(dict(), m.nested_get(obj_level_2, 0, 2))

        self.assertEqual(dict(), m.nested_get(obj_level_3, 2))
        self.assertEqual(dict(), m.nested_get(obj_level_3, 0, 2))
        self.assertEqual(dict(), m.nested_get(obj_level_3, 0, 0, 2))

    def test_missing_level_with_both_dict_and_list(self):
        obj = {"a": [{"b": 1}, {"b": 2}, {"b": 3}], "c": 4}

        self.assertEqual(dict(), m.nested_get(obj, "d"))
        self.assertEqual(dict(), m.nested_get(obj, "a", 3))
        self.assertEqual(dict(), m.nested_get(obj, "a", 0, "d"))


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

        self.spec_full = toml.loads(
            """
[[header.row]]
cell = ["Lorem", "Ipsum", "Dolor"]

[[header.row]]
cell = ["", "", "Sit Amet"]

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

    def test_only_tabular_if_no_title_and_no_label(self):
        result = m.make_template(
            table_spec=dict(),
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
                table_spec=dict(),
                json_filenames=[],
                title=title,
                label=label)

            envs_in_result = re.findall(r"\\begin{([^}]*)}", result)

            self.assertIn("tabular", envs_in_result)
            self.assertNotEqual(["tabular"], envs_in_result)

    def test_column_count_matches_table_spec(self):
        def get_column_count(template):
            match = re.search(r"\\begin{tabular}{lc{(\d+)}}", template)

            self.assertIsNotNone(match)

            return int(match.group(1))

        self.assertEqual(
            1,
            get_column_count(
                m.make_template(
                    table_spec=self.spec_full_with_single_column,
                    json_filenames=["a"],
                    title=None,
                    label=None)))

        for spec in (self.spec_only_body,
                     self.spec_body_and_footer_cell):
            self.assertEqual(
                4,
                get_column_count(
                    m.make_template(
                        table_spec=spec,
                        json_filenames=["a", "b", "c", "d"],
                        title=None,
                        label=None)))

        for spec in (self.spec_body_and_footer_row,
                     self.spec_full):
            self.assertEqual(
                3,
                get_column_count(
                    m.make_template(
                        table_spec=spec,

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
            match = re.search(r"\\begin{tabular}{lc{(\d+)}}", template)

            self.assertIsNotNone(match)

            return int(match.group(1))

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
                (self.spec_full, ["a", "b", "c"]),
                (self.spec_full_with_single_column, ["a"])):
            template = m.make_template(
                table_spec=spec,
                json_filenames=json_filenames,
                title=None,
                label=None)

            column_count = get_column_count(template)
            cell_counts = get_cell_counts(template)

            self.assertTrue(all(x == column_count for x in cell_counts))

