import unittest
from auto_publisher.content_generator import generate_shorts_script


class TestShortsGenerator(unittest.TestCase):
    def test_generate_shorts_script(self):
        data = {"topic": "S&P500 ETF", "price": "5000"}
        try:
            script = generate_shorts_script("S&P500", data, "reveal", lang="ko")
            self.assertIn("title", script)
            self.assertIn("chapters", script)
        except Exception as e:
            self.fail(f"generate_shorts_script failed: {e}")


if __name__ == "__main__":
    unittest.main()
