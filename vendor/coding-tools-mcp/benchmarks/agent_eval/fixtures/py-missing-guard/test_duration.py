import unittest

from textkit.duration import parse_duration


class ParseDurationTests(unittest.TestCase):
    def test_units(self) -> None:
        self.assertEqual(parse_duration("90s"), 90)
        self.assertEqual(parse_duration("2m"), 120)
        self.assertEqual(parse_duration("1h"), 3600)

    def test_empty_string_is_zero(self) -> None:
        self.assertEqual(parse_duration(""), 0)

    def test_unknown_unit_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_duration("5y")


if __name__ == "__main__":
    unittest.main()
