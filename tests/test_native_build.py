from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import install
import selection


class NativeBuildTests(unittest.TestCase):
    def test_inherited_cross_target_cannot_redirect_native_build(self):
        for host, selected_os in [("x86_64-unknown-linux-gnu", "linux"),
                                  ("x86_64-unknown-linux-musl", "linux"),
                                  ("aarch64-apple-darwin", "macos"),
                                  ("x86_64-pc-windows-msvc", "windows")]:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                environment = {"CARGO_BUILD_TARGET": "wasm32-unknown-unknown", "RUSTC": "other-rustc"}
                with patch.object(install.subprocess, "check_output", return_value=f"rustc 1.99.0\nhost: {host}\n"), patch.object(install, "command") as command:
                    result = install.build_native("cargo", "native-rustc", root, selected_os, environment)
                arguments, effective = command.call_args.args
                self.assertEqual(arguments[arguments.index("--target") + 1], host)
                self.assertEqual(effective["RUSTC"], "native-rustc")
                self.assertEqual(environment["RUSTC"], "other-rustc")
                executable = "astra-local-team.exe" if selected_os == "windows" else "astra-local-team"
                self.assertEqual(result, root / "build" / host / "release" / executable)

    def test_missing_duplicate_and_malformed_hosts_stop_before_cargo(self):
        for output in ["rustc 1.99.0\n", "host: \n",
                       "host: x86_64-unknown-linux-gnu\nhost: aarch64-apple-darwin\n",
                       "host: x86_64-unknown-linux-gnu/unsafe\n",
                       "host: x86_64-unknown-linux-gnu\\unsafe\n",
                       "host: -x86_64-unknown-linux-gnu\n",
                       "host: x86_64-unknown-linux-gnu.more\n",
                       "host: x86_64-unknown-linux-gnu extra\n"]:
            with self.subTest(output=output), patch.object(install.subprocess, "check_output", return_value=output), patch.object(install, "command") as command:
                with self.assertRaisesRegex(ValueError, "native host"):
                    install.build_native("cargo", "rustc", Path.cwd(), "linux", {})
                command.assert_not_called()

    def test_overlap_checks_resolve_package_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            alias = source / ".." / "source"
            with patch.object(install, "PACKAGE", alias):
                with self.assertRaisesRegex(ValueError, "separate"):
                    install.main(["--os", selection.host_os(), "--assistant", "custom", "--skills-dir", str(root / "skills"), "--runtime-dir", str(source / "runtime"), "--dry-run"])
            self.assertEqual(list(source.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
