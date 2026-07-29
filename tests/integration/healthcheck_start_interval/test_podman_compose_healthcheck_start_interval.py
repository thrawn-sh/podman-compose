import os
import unittest
from datetime import timedelta

from tests.integration.test_utils import ExecutionTime
from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(test_path(), "healthcheck_start_interval", "docker-compose.yml")


class TestComposeHealthcheckStartInterval(unittest.TestCase, RunSubprocessMixin):
    def test_start_interval_speeds_up_dependency_startup(self) -> None:
        """'healthcheck.start_interval' must drive the healthcheck during 'start_period'.

        The healthcheck of the 'app' service turns healthy on its third run, and 'dependent'
        waits for that. With 'start_interval' honoured this takes a couple of seconds, without
        it the regular 'interval' of 300s would be used.
        """
        try:
            with ExecutionTime(max_execution_time=timedelta(seconds=60)):
                self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                ])

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                "healthcheck_start_interval_app_1",
            ])
            self.assertEqual(output.decode().strip(), "healthy")

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "healthcheck_start_interval_app_1",
                "wc",
                "-l",
                "/tmp/healthchecks",
            ])
            self.assertGreaterEqual(int(output.split()[0]), 3)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
