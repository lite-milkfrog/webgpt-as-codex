import unittest

from textkit import lists


class DedupeTests(unittest.TestCase):
    def test_order_is_preserved(self) -> None:
        self.assertEqual(lists.dedupe([3, 1, 3, 2, 1]), [3, 1, 2])

    def test_empty(self) -> None:
        self.assertEqual(lists.dedupe([]), [])

    def test_flatten_still_works(self) -> None:
        self.assertEqual(lists.flatten([[1, 2], [3]]), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
