import time
import unittest

from src.services.phase8_5_timeout import TimeoutExecutionError, time_limit


class Phase85TimeoutTests(unittest.TestCase):
    def test_time_limit_raises_for_slow_block(self) -> None:
        with self.assertRaises(TimeoutExecutionError):
            with time_limit(0.01, "timeout"):
                time.sleep(0.05)

    def test_time_limit_is_noop_when_timeout_not_configured(self) -> None:
        with time_limit(None, "timeout"):
            time.sleep(0.001)


if __name__ == "__main__":
    unittest.main()