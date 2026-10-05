import unittest

from scripts.index_report import summarize


class SummarizeTests(unittest.TestCase):
    def test_counts_only_indexed_states(self):
        self.assertEqual(summarize(["PASS", "PASS", "NEUTRAL", "inspect_failed", ""]), "구글 색인 2/5편")


if __name__ == "__main__":
    unittest.main()
