"""Unit tests for configuration, credential token, fullscreen, and monitor parsing."""
import os
import unittest
from unittest.mock import patch

from config import Config


class TestConfig(unittest.TestCase):
    def test_default_credential_token(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = Config()
            self.assertEqual(cfg.credential_token, "admin")
            self.assertFalse(cfg.fullscreen)
            self.assertEqual(cfg.monitor, 1)

    def test_env_credential_token_and_fullscreen_and_monitor(self):
        with patch.dict(os.environ, {"password": "env_secret_token", "FULLSCREEN": "true", "OPEN_IN_MONITOR": "2"}, clear=True):
            cfg = Config()
            self.assertEqual(cfg.credential_token, "env_secret_token")
            self.assertTrue(cfg.fullscreen)
            self.assertEqual(cfg.monitor, 2)

        with patch.dict(os.environ, {"PASSWORD": "upper_env_token", "fullscreen": "1", "monitor": "3"}, clear=True):
            cfg = Config()
            self.assertEqual(cfg.credential_token, "upper_env_token")
            self.assertTrue(cfg.fullscreen)
            self.assertEqual(cfg.monitor, 3)

    def test_cli_arg_parsing(self):
        cfg = Config()
        cfg.parse_cli_args(["--password", "custom_cli_pass", "--fullscreen", "true", "--open-in-monitor=2"])
        self.assertEqual(cfg.credential_token, "custom_cli_pass")
        self.assertTrue(cfg.fullscreen)
        self.assertEqual(cfg.monitor, 2)

        cfg.parse_cli_args(["--credential-token", "another_token", "--fullscreen", "false", "--monitor", "1"])
        self.assertEqual(cfg.credential_token, "another_token")
        self.assertFalse(cfg.fullscreen)
        self.assertEqual(cfg.monitor, 1)

        # Bare flag --fullscreen and -m
        cfg.parse_cli_args(["--fullscreen", "-m", "2"])
        self.assertTrue(cfg.fullscreen)
        self.assertEqual(cfg.monitor, 2)


if __name__ == "__main__":
    unittest.main()
