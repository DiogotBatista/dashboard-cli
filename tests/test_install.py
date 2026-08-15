import os
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class InstallTest(TestCase):
    def test_creates_global_launcher_in_user_local_bin(self):
        with tempfile.TemporaryDirectory() as home:
            environment = {**os.environ, "HOME": home}

            subprocess.run([ROOT / "bin" / "install"], check=True, env=environment)

            launcher = Path(home) / ".local" / "bin" / "ai-dashboard"
            self.assertTrue(launcher.is_symlink())
            self.assertEqual(launcher.resolve(), (ROOT / "bin" / "dashboard").resolve())
