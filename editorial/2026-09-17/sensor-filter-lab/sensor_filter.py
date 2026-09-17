"""Controlled arithmetic example, not a robot or sensor benchmark. Python 3.12+."""
import argparse
import math


def moving_average(values, window):
    """Causal full-window mean. Missing startup outputs are None, not zero."""
    if type(window) is not int or window < 1:
        raise ValueError("window must be a positive integer")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("samples must be finite")
    return [None if index < window - 1 else
            sum(values[index - window + 1:index + 1]) / window
            for index in range(len(values))]


def experiment():
    period_ms = 10
    # Deterministic alternating noise, NOT independent random noise.
    stationary = [1.0 + (0.2 if index % 2 == 0 else -0.2)
                  for index in range(40)]
    # Separate noiseless step so threshold time is not driven by noise.
    step = [0.0] * 20 + [1.0] * 20
    rows = []
    for window in (1, 3, 5):
        smooth = moving_average(stationary, window)
        # Same 36 sample positions for all filters; no warm-up None values.
        rms = math.sqrt(sum((value - 1.0) ** 2 for value in smooth[4:]) / 36)
        response = moving_average(step, window)
        first = next(index for index in range(20, 40) if response[index] >= 0.9)
        rows.append((window, rms, (first - 20) * period_ms))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--invalid-window", type=int)
    args = parser.parse_args()
    if args.invalid_window is not None:
        try:
            moving_average([1.0], args.invalid_window)
        except ValueError as error:
            parser.exit(2, f"ERROR: {error}\n")
    print("controlled example: alternating noise; separate noiseless step")
    print("sample_interval_ms=10; rms_positions=4..39; step_index=20")
    print("window  stationary_rms_m  step90_delay_ms")
    for window, rms, delay in experiment():
        print(f"{window:>6}  {rms:>16.6f}  {delay:>15}")


if __name__ == "__main__":
    main()
