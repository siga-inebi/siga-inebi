import contextlib
import io
import time
import unittest

from scan_load_test import (
    MIN_MEASURED_PER_ROUND,
    add_warmup_failures,
    code_offset,
    main,
    percentile,
    run_round,
    summarize,
    summarize_rounds,
)


def sample(seconds, status=200, outcome="created"):
    return {"seconds": seconds, "status": status, "outcome": outcome}


class PercentileTests(unittest.TestCase):
    def test_nearest_rank(self):
        values = [float(n) for n in range(1, 101)]
        self.assertEqual(percentile(values, 50), 50.0)
        self.assertEqual(percentile(values, 95), 95.0)
        self.assertEqual(percentile(values, 99), 99.0)

    def test_single_value(self):
        self.assertEqual(percentile([0.3], 95), 0.3)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            percentile([], 95)


class SummarizeTests(unittest.TestCase):
    def test_all_ok_within_limit(self):
        report = summarize([sample(0.1), sample(0.2), sample(0.3)], 1.0, 3)
        self.assertTrue(report["p95_within_limit"])
        self.assertEqual(report["lost_or_failed_events"], 0)
        self.assertEqual(report["throughput_per_second"], 3.0)

    def test_slow_p95_fails_limit(self):
        report = summarize([sample(0.1)] * 18 + [sample(2.5)] * 2, 5.0, 2)
        self.assertFalse(report["p95_within_limit"])

    def test_errors_are_counted_not_hidden(self):
        report = summarize([sample(0.1), sample(0.1, 500, ""), sample(0.0, 0, "URLError")], 1.0, 1)
        self.assertEqual(report["lost_or_failed_events"], 2)
        self.assertEqual(report["failures"], {"500:": 1, "0:URLError": 1})

    def test_duplicate_outcome_is_not_created(self):
        report = summarize([sample(0.1, 200, "duplicate")], 1.0, 1)
        self.assertEqual(report["lost_or_failed_events"], 1)

    def test_no_successes_never_passes(self):
        self.assertFalse(summarize([sample(0.1, 500, "")], 1.0, 1)["p95_within_limit"])


class ProtocolTests(unittest.TestCase):
    def test_success_rate_and_network_errors_reported_separately(self):
        report = summarize(
            [
                sample(0.1),
                sample(0.1),
                sample(0.0, 0, "TimeoutError"),
                sample(0.1, 500, ""),
            ],
            1.0,
            1,
        )
        self.assertEqual(report["success_rate_percent"], 50.0)
        self.assertEqual(report["network_errors"], 1)

    def test_code_offsets_never_overlap_between_rounds_and_operators(self):
        used = set()
        for rnd in range(3):
            for op in range(3):
                start = code_offset(rnd, op, 3, per_operator=10, warmup=2)
                block = set(range(start, start + 12))
                self.assertFalse(used & block)
                used |= block

    def test_every_round_must_pass_and_meet_sample_size(self):
        good = summarize([sample(0.1)] * MIN_MEASURED_PER_ROUND, 10.0, 3)
        slow = summarize([sample(0.1)] * 90 + [sample(2.5)] * 10, 10.0, 3)
        self.assertTrue(summarize_rounds([good, good, good])["p95_within_limit"])
        self.assertFalse(summarize_rounds([good, slow, good])["p95_within_limit"])

    def test_small_sample_is_flagged(self):
        small = summarize([sample(0.1)] * 20, 2.0, 3)
        result = summarize_rounds([small])
        self.assertFalse(result["meets_min_sample"])
        self.assertEqual(result["measured_per_round_min"], 20)

    def test_pooled_totals_cover_all_rounds(self):
        a = summarize([sample(0.1)] * 100, 10.0, 3)
        b = summarize([sample(0.2, 500, "")] * 5 + [sample(0.2)] * 95, 10.0, 3)
        result = summarize_rounds([a, b])
        self.assertEqual(result["requests"], 200)
        self.assertEqual(result["lost_or_failed_events"], 5)


class FakeOperator:
    """Escanea sin red: ``slow`` segundos en calentamiento, instantaneo al medir."""

    def __init__(self, warmup, slow=0.0, warmup_status=(200, "created")):
        self.calls = 0
        self.warmup = warmup
        self.slow = slow
        self.warmup_status = warmup_status

    def scan(self, item):
        self.calls += 1
        if self.calls <= self.warmup:
            time.sleep(self.slow)
            return self.warmup_status
        return 200, "created"


SEED = {"student_codes": [f"S{n}" for n in range(100)], "shift_id": "s", "control_point_id": "c"}


class WarmupTests(unittest.TestCase):
    def test_lost_warmup_events_are_counted_not_hidden(self):
        summary = summarize([sample(0.1)], wall_seconds=1.0, operators=1)
        warmup = [sample(0.1), sample(0.1, status=0, outcome="URLError"), sample(0.1, 500, "")]

        result = add_warmup_failures(summary, warmup)

        self.assertEqual(result["warmup_requests"], 3)
        self.assertEqual(result["warmup_lost_or_failed"], 2)
        self.assertEqual(result["warmup_network_errors"], 1)
        self.assertEqual(result["lost_or_failed_events"], 2)
        self.assertNotIn("URLError", str(result["failures"]))  # fuera de los percentiles

    def test_round_with_lost_warmup_event_reports_it(self):
        clients = [FakeOperator(warmup=2, warmup_status=(0, "URLError"))]

        result = run_round(clients, SEED, 0, per_operator=3, warmup=2, think=0.0)

        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["created"], 3)
        self.assertEqual(result["lost_or_failed_events"], 2)

    def test_throughput_window_excludes_warmup(self):
        clients = [FakeOperator(warmup=2, slow=0.2) for _ in range(2)]

        result = run_round(clients, SEED, 0, per_operator=5, warmup=2, think=0.0)

        self.assertLess(result["wall_seconds"], 0.2)


class ArgumentTests(unittest.TestCase):
    def assert_rejected(self, *extra):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            main(["--seed", "unused.json", *extra])
        self.assertEqual(ctx.exception.code, 2)

    def test_rejects_zero_rounds(self):
        self.assert_rejected("--rounds", "0")

    def test_rejects_negative_warmup(self):
        self.assert_rejected("--warmup", "-1")

    def test_rejects_zero_operators(self):
        self.assert_rejected("--operators", "0")


if __name__ == "__main__":
    unittest.main()
