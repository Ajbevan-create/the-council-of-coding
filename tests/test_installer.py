import contextlib
import hashlib
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
import selection


class SelectionTests(unittest.TestCase):
    def test_os_selection_is_explicit_and_matches_host(self):
        for platform_name, name in [("Linux", "linux"), ("Darwin", "macos"), ("Windows", "windows")]:
            with patch.object(selection.platform, "system", return_value=platform_name):
                self.assertEqual(selection.select_os(name), name)
                with self.assertRaisesRegex(ValueError, "running on"):
                    selection.select_os("macos" if name != "macos" else "linux")

    def test_missing_noninteractive_choices_stop(self):
        with patch.object(selection.sys.stdin, "isatty", return_value=False):
            for function in [selection.select_os, selection.select_assistants]:
                with self.assertRaisesRegex(ValueError, "Explicit choices required"):
                    function()

    def test_blank_invalid_and_zero_do_not_select_a_default(self):
        with patch.object(selection.sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=["", "0", "9", "bad", "2"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(selection.choose("OS", ["linux", "macos", "windows"]), "macos")

    def test_assistants_all_multiple_and_custom(self):
        self.assertEqual(selection.select_assistants("codex,gemini,codex"), ["codex", "gemini"])
        self.assertEqual(selection.select_assistants("all"), selection.ASSISTANTS[:6])
        self.assertEqual(selection.select_assistants("all,custom")[-1], "custom")
        for value in ["", "codex,", "unsupported"]:
            with self.assertRaises(ValueError):
                selection.select_assistants(value)

    def test_paths_use_recipient_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_home = Path(temporary)
            suffix = "astra-local-orchestrator"
            expected = {"codex": ".agents/skills", "generic": ".agents/skills", "claude-code": ".claude/skills", "opencode": ".config/opencode/skills", "gemini": ".gemini/skills"}
            for assistant, folder in expected.items():
                self.assertEqual(selection.target_paths(assistant, user_home, {}), [user_home / folder / suffix])
            self.assertEqual(selection.target_paths("perplexity", user_home, {}), [])
            self.assertEqual(selection.target_paths("codex", user_home, {"CODEX_HOME": str(user_home / "codex-root")}), [user_home / "codex-root/skills" / suffix])
            self.assertEqual(selection.target_paths("opencode", user_home, {"XDG_CONFIG_HOME": str(user_home / "config")}), [user_home / "config/opencode/skills" / suffix])
            self.assertEqual(selection.target_paths("opencode", user_home, {"XDG_CONFIG_HOME": ""}), [user_home / ".config/opencode/skills" / suffix])
            with self.assertRaises(ValueError):
                selection.target_paths("custom", user_home, {})
            with self.assertRaises(ValueError):
                selection.target_paths("codex", user_home, {"CODEX_HOME": "relative"})


class InstallationTests(unittest.TestCase):
    def test_cli_requires_both_choices(self):
        for options in [[], ["--os", selection.host_os()], ["--assistant", "custom"]]:
            process = subprocess.run([sys.executable, str(PACKAGE / "scripts/install.py"), *options, "--dry-run"], stdin=subprocess.DEVNULL, capture_output=True, text=True)
            self.assertEqual(process.returncode, 1)
            self.assertIn("Explicit choices required", process.stderr)

    def test_dry_run_performs_no_build_network_or_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(install, "api", side_effect=AssertionError("network")), patch.object(install, "command", side_effect=AssertionError("build")), patch.object(install, "verify_package", side_effect=AssertionError("manifest")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(install.main(["--os", selection.host_os(), "--assistant", "custom", "--skills-dir", str(root / "skills"), "--runtime-dir", str(root / "runtime"), "--dry-run"]), 0)
            self.assertEqual(list(root.iterdir()), [])

    def test_overlap_is_rejected_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "source"
            package.mkdir()
            with patch.object(install, "PACKAGE", package), contextlib.redirect_stdout(io.StringIO()):
                for runtime, skills in [(package / "runtime", root / "skills"), (root / "runtime", package / "skills"), (root / "skills/astra-local-orchestrator/runtime", root / "skills")]:
                    with self.assertRaisesRegex(ValueError, "separate"):
                        install.main(["--os", selection.host_os(), "--assistant", "custom", "--skills-dir", str(skills), "--runtime-dir", str(runtime), "--dry-run"])
            self.assertEqual(list(package.iterdir()), [])

    def test_manifest_detects_corruption_and_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "file.txt"
            source.write_text("original", encoding="utf-8")
            (root / "SHA256SUMS").write_text(install.digest(source) + "  file.txt\n", encoding="utf-8")
            install.verify_package(root)
            source.write_text("corrupt", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                install.verify_package(root)
            (root / "SHA256SUMS").write_text("0" * 64 + "  ../outside\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid"):
                install.verify_package(root)

    def test_download_verified_before_import_and_cache_reused(self):
        payload = b"fake weights for contract validation"
        model = {"role": "test", "alias": "test:local", "filename": "test.gguf", "url": "https://example.invalid/test", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            with patch.object(install.urllib.request, "urlopen", return_value=io.BytesIO(payload)):
                result = install.download(model, root)
                self.assertEqual(result.read_bytes(), payload)
            with patch.object(install.urllib.request, "urlopen", side_effect=AssertionError("cached download")):
                self.assertEqual(install.download(model, root), result)
            result.unlink()
            with patch.object(install.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    install.download(model, root)
            self.assertFalse(result.exists())

    def test_conflicting_alias_is_not_overwritten(self):
        model = {"alias": "test:local", "sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as temporary, patch.object(install, "api", side_effect=[{"models": [{"name": "test:local"}]}, {"modelfile": "different weights"}]), patch.object(install, "command") as command:
            with self.assertRaisesRegex(ValueError, "replace-models"):
                install.install_models([model], Path(temporary), "ollama", {})
            command.assert_not_called()

    def test_matching_alias_is_reused_without_download(self):
        model = {"alias": "test:local", "sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as temporary, patch.object(install, "api", side_effect=[{"models": [{"name": "test:local"}]}, {"modelfile": "FROM sha256-" + model["sha256"]}]), patch.object(install, "download") as download:
            receipt = install.install_models([model], Path(temporary), "ollama", {})
            self.assertEqual(receipt[0]["action"], "reused")
            download.assert_not_called()

    def test_modelfile_quotes_spaces_and_rejects_injection(self):
        with tempfile.TemporaryDirectory(prefix="path with spaces ") as temporary:
            weights = Path(temporary) / "model.gguf"
            model = {"parameters": {"temperature": 0.6}}
            self.assertTrue(install.modelfile(model, weights).startswith('FROM "' + weights.as_posix() + '"\n'))
            with self.assertRaises(ValueError):
                install.modelfile(model, Path(temporary) / 'bad"name')

    def test_upgrade_preserves_backup_and_new_runtime_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("new skill", encoding="utf-8")
            destination = root / "skills/astra-local-orchestrator"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("old skill", encoding="utf-8")
            with patch.object(install, "PACKAGE", source):
                with self.assertRaises(ValueError):
                    install.copy_skill(destination, root / "runtime", root / "runner")
                with contextlib.redirect_stdout(io.StringIO()):
                    install.copy_skill(destination, root / "runtime", root / "runner", upgrade=True)
            backups = list((root / "runtime/skill-backups").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "SKILL.md").read_text(encoding="utf-8"), "old skill")
            self.assertEqual(list(destination.parent.iterdir()), [destination])
            self.assertEqual(json.loads((destination / "runtime.json").read_text(encoding="utf-8"))["binary"], str(root / "runner"))

    def test_failed_copy_keeps_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "skill"
            destination.mkdir()
            (destination / "keep").write_text("old", encoding="utf-8")
            with patch.object(install.shutil, "copytree", side_effect=OSError("copy failure")):
                with self.assertRaises(OSError):
                    install.copy_skill(destination, root / "runtime", root / "runner", upgrade=True)
            self.assertEqual((destination / "keep").read_text(encoding="utf-8"), "old")
            self.assertFalse((root / "runtime/skill-backups").exists())

    def test_failed_final_rename_restores_old_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("new", encoding="utf-8")
            destination = root / "skill"
            destination.mkdir()
            (destination / "SKILL.md").write_text("old", encoding="utf-8")
            with patch.object(install, "PACKAGE", source), patch.object(Path, "rename", side_effect=OSError("final rename failed")), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(OSError, "final rename failed"):
                    install.copy_skill(destination, root / "runtime", root / "runner", upgrade=True)
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "old")
            self.assertFalse(list(root.glob(".astra-install-*")))


if __name__ == "__main__":
    unittest.main()
