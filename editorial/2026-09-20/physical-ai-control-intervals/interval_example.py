"""Own one-dimensional arithmetic model; no robot, clock, or ROS execution."""
from fractions import Fraction as F
import argparse
import unittest


def displacement(speed_m_s, intervals_ms):
    intervals = [F(str(value)) / 1000 for value in intervals_ms]
    if not intervals or any(dt <= 0 for dt in intervals):
        raise ValueError("intervals must be nonempty and strictly positive")
    return F(str(speed_m_s)) * sum(intervals, F(0))


class IntervalTests(unittest.TestCase):
    def test_variable_intervals(self):
        self.assertEqual(displacement("0.4", [20, 30, 40]), F(36, 1000))

    def test_nominal_assumption(self):
        self.assertEqual(displacement("0.4", [20, 20, 20]), F(24, 1000))

    def test_subdivision(self):
        self.assertEqual(displacement("0.4", [20] * 3), displacement("0.4", [10] * 6))

    def test_direction(self):
        self.assertEqual(displacement("-0.4", [20, 30, 40]), F(-36, 1000))

    def test_stationary(self):
        self.assertEqual(displacement("0", [20, 30, 40]), 0)

    def test_invalid_intervals(self):
        for intervals in ([], [0], [-1], [20, 0]):
            with self.subTest(intervals=intervals), self.assertRaises(ValueError):
                displacement("0.4", intervals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-ms", type=int, nargs="+", default=[20, 30, 40])
    args = parser.parse_args()
    try:
        actual = displacement("0.4", args.interval_ms)
    except ValueError as exc:
        parser.error(str(exc))
    nominal = displacement("0.4", [20] * len(args.interval_ms))
    print(f"elapsed_ms={sum(args.interval_ms)}")
    print(f"interval_aware_displacement_m={float(actual):.3f}")
    print(f"nominal_20ms_displacement_m={float(nominal):.3f}")
    print(f"nominal_minus_interval_aware_m={float(nominal - actual):.3f}")
    print(f"same_duration_subdivision_m={float(displacement('0.4', [10] * 6)):.3f}")


if __name__ == "__main__":
    main()
