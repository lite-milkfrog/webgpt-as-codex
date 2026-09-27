import unittest

from textkit.chunker import chunk


class ChunkTests(unittest.TestCase):
    def test_even_split(self) -> None:
        self.assertEqual(chunk([1, 2, 3, 4], 2), [[1, 2], [3, 4]])

    def test_the_final_partial_chunk_is_kept(self) -> None:
        self.assertEqual(chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_empty_input(self) -> None:
        self.assertEqual(chunk([], 3), [])

    def test_size_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            chunk([1], 0)


if __name__ == "__main__":
    unittest.main()
