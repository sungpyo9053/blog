import math
import unittest
from sensor_filter import experiment, moving_average


class FilterTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(moving_average([1, 2, 3], 1), [1, 2, 3])

    def test_warmup_and_hand_calculation(self):
        self.assertEqual(moving_average([1, 2, 6, 10], 3), [None, None, 3, 6])

    def test_no_future_samples(self):
        self.assertEqual(moving_average([0, 0, 0, 1, 1, 1], 3),
                         [None, None, 0, 1 / 3, 2 / 3, 1])

    def test_invalid_windows(self):
        for window in (0, -1, True, 2.5):
            with self.assertRaises(ValueError):
                moving_average([1], window)

    def test_nonfinite_input(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                moving_average([value], 1)

    def test_short_and_empty_inputs(self):
        self.assertEqual(moving_average([1], 3), [None])
        self.assertEqual(moving_average([], 3), [])

    def test_bias_is_not_removed(self):
        self.assertEqual(moving_average([1.2] * 6, 5)[-1], 1.2)

    def test_known_noise_and_step_results(self):
        for row, expected in zip(experiment(), [(1, .2, 0), (3, .2 / 3, 20), (5, .04, 40)]):
            self.assertEqual(row[0], expected[0])
            self.assertAlmostEqual(row[1], expected[1])
            self.assertEqual(row[2], expected[2])


if __name__ == "__main__":
    unittest.main()
