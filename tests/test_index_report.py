import unittest

from scripts.index_report import summarize


class SummarizeTests(unittest.TestCase):
    def test_counts_only_indexed_states(self):
        states = ["Submitted and indexed", "Indexed, not submitted in sitemap",
                  "Discovered - currently not indexed", "URL is unknown to Google", ""]
        self.assertEqual(summarize(states), "구글 색인 2/5편")


if __name__ == "__main__":
    unittest.main()
