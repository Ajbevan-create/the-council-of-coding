import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PACKAGE / "scripts"))
import mcp_bridge
import run


class McpTests(unittest.TestCase):
    def test_stdio_handshake_discovery_and_protocol_fallback(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {"text": "Příliš žluťoučký"}},
            {"jsonrpc": "2.0", "id": 4, "method": "server/discover"},
        ]
        process = subprocess.run([sys.executable, str(PACKAGE / "scripts/mcp_bridge.py")], input="".join(json.dumps(item, ensure_ascii=False) + "\n" for item in requests), capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, "")
        answers = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([item["id"] for item in answers], [1, 2, 3, 4])
        self.assertEqual(answers[0]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual([tool["name"] for tool in answers[1]["result"]["tools"]], ["astra_local_doctor", "astra_local_propose"])
        self.assertEqual(answers[3]["error"]["code"], -32601)

    def test_propose_only_calls_fixed_runner_never_proposed_actions(self):
        with tempfile.TemporaryDirectory(prefix="council path ") as temporary:
            root = Path(temporary)
            binary = root / "astra-local-team"
            report = {"execution": "not_executed", "actions": [{"argv": ["DO_NOT_EXECUTE", "user command"]}]}
            completed = subprocess.CompletedProcess([], 0, json.dumps(report), "")
            with patch.object(mcp_bridge, "runtime_config", return_value=(binary, root)), patch.object(mcp_bridge.subprocess, "run", return_value=completed) as command:
                answer = mcp_bridge.tool_call("astra_local_propose", {"workspace": str(root), "brief": "A bounded task", "rounds": 1})
            command.assert_called_once()
            argv = command.call_args.args[0]
            self.assertEqual(argv[:3], [str(binary), "--workspace", str(root)])
            self.assertNotIn("DO_NOT_EXECUTE", argv)
            self.assertEqual(Path(argv[4]).read_text(encoding="utf-8"), "A bounded task")
            self.assertFalse(answer["isError"])
            self.assertEqual(json.loads(answer["content"][0]["text"]), report)

    def test_invalid_proposals_never_spawn_runner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = {"workspace": str(root), "brief": "bounded"}
            invalid = [{"workspace": "relative"}, {"brief": "é" * 4001}, {"rounds": True}, {"rounds": 4}, {"model": "unlisted"}, {"resume_dir": str(root)}, {"arbitrary_command": "anything"}]
            with patch.object(mcp_bridge, "runtime_config", return_value=(root / "runner", root)), patch.object(mcp_bridge.subprocess, "run") as command:
                for changes in invalid:
                    with self.assertRaises(ValueError):
                        mcp_bridge.tool_call("astra_local_propose", dict(baseline, **changes))
                command.assert_not_called()
            self.assertFalse((root / "bridge-inputs").exists())

    def test_doctor_is_read_only_and_returns_runner_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(mcp_bridge, "runtime_config", return_value=(root / "runner", root)), patch.object(mcp_bridge.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, '{"status":"unavailable"}', "")) as command:
                answer = mcp_bridge.tool_call("astra_local_doctor", {})
                self.assertEqual(command.call_args.args[0], [str(root / "runner"), "--doctor"])
                self.assertTrue(answer["isError"])
            self.assertEqual(list(root.iterdir()), [])

    def test_malformed_runtime_configuration_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            (root / "runtime.json").write_text('{"bad":"config"}', encoding="utf-8")
            with patch.object(run, "__file__", str(scripts / "run.py")):
                with self.assertRaisesRegex(ValueError, "Invalid runtime configuration"):
                    run.runtime_config()


if __name__ == "__main__":
    unittest.main()
