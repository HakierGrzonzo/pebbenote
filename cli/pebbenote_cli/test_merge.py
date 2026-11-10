from unittest import TestCase

from .merge import has_markers, merge3

BASE = "- milk\n- eggs\n- flour\n"


class Merge3TestCase(TestCase):
    def test_only_mine_changed(self):
        mine = "- oat milk\n- eggs\n- flour\n"

        self.assertEqual(merge3(BASE, mine, BASE), (mine, False))

    def test_only_theirs_changed(self):
        theirs = "- milk\n- eggs\n- flour\n- sugar\n"

        self.assertEqual(merge3(BASE, BASE, theirs), (theirs, False))

    def test_changes_in_different_places_merge(self):
        mine = "- oat milk\n- eggs\n- flour\n"
        theirs = "- milk\n- eggs\n- flour\n- sugar\n"

        self.assertEqual(
            merge3(BASE, mine, theirs),
            ("- oat milk\n- eggs\n- flour\n- sugar\n", False),
        )

    def test_delete_and_add_merge(self):
        mine = "- milk\n- flour\n"
        theirs = "- butter\n- milk\n- eggs\n- flour\n"

        self.assertEqual(
            merge3(BASE, mine, theirs), ("- butter\n- milk\n- flour\n", False)
        )

    def test_same_change_on_both_sides(self):
        both = "- soy milk\n- eggs\n- flour\n"

        self.assertEqual(merge3(BASE, both, both), (both, False))

    def test_same_line_changed_differently_conflicts(self):
        mine = "- oat milk\n- eggs\n- flour\n"
        theirs = "- soy milk\n- eggs\n- flour\n- sugar\n"

        merged, has_conflicts = merge3(BASE, mine, theirs)

        self.assertTrue(has_conflicts)
        self.assertEqual(
            merged,
            "<<<<<<< yours\n"
            "- oat milk\n"
            "=======\n"
            "- soy milk\n"
            ">>>>>>> server\n"
            "- eggs\n"
            "- flour\n"
            "- sugar\n",
        )

    def test_both_added_at_the_end_conflicts(self):
        merged, has_conflicts = merge3(BASE, BASE + "- salt\n", BASE + "- sugar\n")

        self.assertTrue(has_conflicts)
        self.assertEqual(
            merged,
            BASE + "<<<<<<< yours\n- salt\n=======\n- sugar\n>>>>>>> server\n",
        )

    def test_missing_final_newline_is_no_change(self):
        self.assertEqual(merge3("- milk", "- milk\n", "- milk\n- eggs")[1], False)

    def test_everything_replaced_from_empty(self):
        self.assertEqual(merge3("", "- mine\n", ""), ("- mine\n", False))

    def test_has_markers(self):
        merged, _ = merge3(BASE, "- a\n", "- b\n")

        self.assertTrue(has_markers(merged))
        self.assertFalse(has_markers(BASE))
        # A plain separator line can be part of a note
        self.assertFalse(has_markers("Title\n=======\n- milk\n"))
