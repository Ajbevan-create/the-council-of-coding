import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PACKAGE / "scripts"))
import install


class RuntimeInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="runtime upgrade ")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.source = base / "source"
        (self.source / "scripts").mkdir(parents=True)
        (self.source / "scripts/run.py").write_text("new adapter", encoding="utf-8")
        self.build = base / "build/runner.exe"
        self.build.parent.mkdir()
        self.build.write_text("new binary", encoding="utf-8")
        self.root = base / "runtime"
        (self.root / "bin").mkdir(parents=True)
        (self.root / "bin/runner.exe").write_text("old binary", encoding="utf-8")
        (self.root / "adapter").mkdir()
        (self.root / "adapter/run.py").write_text("old adapter", encoding="utf-8")
        for filename in ["runtime.json", "mcp-config.json"]:
            (self.root / filename).write_text("old config", encoding="utf-8")

    def assert_original_intact(self):
        self.assertEqual((self.root / "bin/runner.exe").read_text(encoding="utf-8"), "old binary")
        self.assertEqual((self.root / "adapter/run.py").read_text(encoding="utf-8"), "old adapter")
        for filename in ["runtime.json", "mcp-config.json"]:
            self.assertEqual((self.root / filename).read_text(encoding="utf-8"), "old config")
        self.assertFalse(list(self.root.glob(".runtime-install-*")))

    def test_doctor_failure_does_not_replace_existing_runtime(self):
        with patch.object(install, "PACKAGE", self.source), patch.object(install, "command", side_effect=subprocess.CalledProcessError(1, ["runner", "--doctor"])):
            with self.assertRaises(subprocess.CalledProcessError):
                install.install_runtime(self.build, self.root, {})
        self.assert_original_intact()

    def test_adapter_copy_failure_does_not_replace_existing_runtime(self):
        with patch.object(install, "PACKAGE", self.source), patch.object(install.shutil, "copytree", side_effect=OSError("adapter copy failed")), patch.object(install, "command") as command:
            with self.assertRaisesRegex(OSError, "adapter copy failed"):
                install.install_runtime(self.build, self.root, {})
            command.assert_not_called()
        self.assert_original_intact()

    def test_activation_failure_rolls_back_binary_and_adapter(self):
        replace = install.os.replace
        def fail_adapter(source, target):
            if Path(target).name == "adapter":
                raise OSError("adapter activation failed")
            return replace(source, target)
        with patch.object(install, "PACKAGE", self.source), patch.object(install, "command"), patch.object(install.os, "replace", side_effect=fail_adapter):
            with self.assertRaisesRegex(OSError, "adapter activation failed"):
                install.install_runtime(self.build, self.root, {})
        self.assert_original_intact()

    def test_success_keeps_previous_runtime_and_uses_final_paths(self):
        with patch.object(install, "PACKAGE", self.source), patch.object(install, "command") as command, contextlib.redirect_stdout(io.StringIO()):
            binary = install.install_runtime(self.build, self.root, {})
        self.assertEqual(binary, self.root / "bin/runner.exe")
        self.assertEqual(binary.read_text(encoding="utf-8"), "new binary")
        self.assertEqual((self.root / "adapter/run.py").read_text(encoding="utf-8"), "new adapter")
        old = list((self.root / "runtime-backups").iterdir())
        self.assertEqual(len(old), 1)
        self.assertEqual((old[0] / "runner.exe").read_text(encoding="utf-8"), "old binary")
        self.assertEqual((old[0] / "adapter/run.py").read_text(encoding="utf-8"), "old adapter")
        config = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(config["binary"], str(binary))
        mcp = json.loads((self.root / "mcp-config.json").read_text(encoding="utf-8"))["mcpServers"]["astra-local-council"]
        self.assertEqual(mcp["args"], [str(self.root / "adapter/mcp_bridge.py")])
        command.assert_called_once()
        self.assertNotEqual(Path(command.call_args.args[0][0]), binary)


if __name__ == "__main__":
    unittest.main()
