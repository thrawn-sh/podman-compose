# SPDX-License-Identifier: GPL-2.0

# pylint: disable=protected-access
import unittest
from unittest import mock

from parameterized import parameterized

from podman_compose import emulate_start_interval
from podman_compose import parse_duration_seconds


class TestParseDurationSeconds(unittest.TestCase):
    @parameterized.expand([
        ("10s", 10.0),
        ("1m30s", 90.0),
        ("500ms", 0.5),
        ("1h", 3600.0),
        ("1h2m3s4ms5us", 3723.004005),
        ("  10s  ", 10.0),
        (5, 5.0),
        (1.5, 1.5),
    ])
    def test_valid(self, value: object, expected: float) -> None:
        result = parse_duration_seconds(value)  # type: ignore[arg-type]
        assert result is not None
        self.assertAlmostEqual(result, expected)

    @parameterized.expand([(None,), ("",), ("10",), ("abc",), ("10 s",), ("10sx",)])
    def test_invalid(self, value: object) -> None:
        self.assertIsNone(parse_duration_seconds(value))  # type: ignore[arg-type]


class TestEmulateStartInterval(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.compose = mock.Mock()
        self.compose.podman.output = mock.AsyncMock(return_value=b"starting\n")

    def get_container(self, **healthcheck: object) -> dict:
        return {"name": "cnt", "healthcheck": healthcheck}

    async def test_no_start_interval_does_nothing(self) -> None:
        await emulate_start_interval(self.compose, self.get_container(start_period="10s"))
        self.compose.podman.output.assert_not_called()

    async def test_no_start_period_does_nothing(self) -> None:
        await emulate_start_interval(self.compose, self.get_container(start_interval="1ms"))
        self.compose.podman.output.assert_not_called()

    async def test_runs_healthcheck_until_start_period_elapsed(self) -> None:
        cnt = self.get_container(start_interval="1ms", start_period="20ms")
        await emulate_start_interval(self.compose, cnt)

        calls = self.compose.podman.output.call_args_list
        healthcheck_runs = [c for c in calls if c.args[1] == "healthcheck"]
        self.assertGreater(len(healthcheck_runs), 1)
        for call in healthcheck_runs:
            self.assertEqual(call.args[2], ["run", "cnt"])

    async def test_stops_once_container_is_no_longer_starting(self) -> None:
        self.compose.podman.output = mock.AsyncMock(return_value=b"healthy\n")
        cnt = self.get_container(start_interval="1ms", start_period="10s")

        await emulate_start_interval(self.compose, cnt)

        calls = self.compose.podman.output.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[1], "inspect")
