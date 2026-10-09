"""Proves scripts/security_scan.py works: every check is shown to fire on
a planted bad line (in strings and temporary files here, never in the
real code), and to stay quiet on normal code."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SPEC = importlib.util.spec_from_file_location(
    "security_scan", Path(__file__).resolve().parent.parent / "scripts" / "security_scan.py")
scan = importlib.util.module_from_spec(_SPEC)
# Register it before running it: @dataclass looks its module up in
# sys.modules while building the class (with `from __future__ import
# annotations`), and a module loaded by hand isn't there yet.
sys.modules["security_scan"] = scan
_SPEC.loader.exec_module(scan)

# Every planted example is built from pieces ("os" + ".system"), so this
# file doesn't itself contain the patterns and passes its own scan.
EV, EX = "ev" + "al", "ex" + "ec"
KEY_HEADER = "-----BEGIN RSA " + "PRIVATE KEY-----"
EMAIL = "someone" + "@" + "gmail.com"


def kinds(path, text):
    return [f.kind for f in scan.scan_text(path, text)]


class TestDangerousPatterns(unittest.TestCase):
    def test_each_pattern_fires_on_a_planted_line(self):
        planted = {
            "eval/exec": f"x = {EV}(user_input)",
            "pickle/marshal (unsafe deserialisation)": "data = pickle" + ".loads(blob)",
            "shell command": "os" + ".system('dir')",
            "subprocess": "import " + "subprocess",
            "unsafe YAML load": "cfg = yaml" + ".load(text)",
            "dynamic import": "m = __imp" + "ort__(name)",
            "listening on all interfaces": "server = HTTPServer(('" + ".".join("0" * 4) + "', 80), H)",
            "TLS verification off": "requests.get(url, verify" + "=False)",
            "insecure temp file": "name = tempfile" + ".mktemp()",
        }
        for kind, line in planted.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, kinds("src/x.py", line))

    def test_exec_too(self):
        self.assertIn("eval/exec", kinds("src/x.py", f"{EX}(code)"))

    def test_normal_code_is_quiet(self):
        normal = "\n".join([
            "import json",
            "value = json.loads(text)",
            "server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)",
            "evaluation = evaluate(model)",       # 'eval' only as part of a word
            "cfg = yaml.load(text, Loader=yaml.SafeLoader)",
        ])
        self.assertEqual(kinds("src/x.py", normal), [])

    def test_allow_comment_opts_a_line_out_but_only_for_patterns(self):
        self.assertEqual(kinds("src/x.py", "import subprocess  # security-scan: allow fixed args, no shell"), [])
        self.assertIn("personal email address", kinds("src/x.py", f"x = '{EMAIL}'  # security-scan: allow"))

    def test_patterns_only_apply_to_python(self):
        self.assertEqual(kinds("docs/X.md", f"Never call `{EV}(...)` on input."), [])


class TestInvariants(unittest.TestCase):
    def test_secrets_and_personal_data_fire_in_any_file(self):
        self.assertIn("private key", kinds("notes.md", KEY_HEADER))
        self.assertIn("GitHub token", kinds("x.py", "token = 'ghp_" + "a" * 36 + "'"))
        self.assertIn("AWS access key", kinds("x.toml", "key = AKIA" + "A" * 16))
        self.assertIn("JSON web token", kinds("x.md", "ey" + "JhbGciOiJSUzI1NiJ9.ey" + "JzdWIiOiJ1c2VyIn0.sig"))
        self.assertIn("personal email address", kinds("README.md", f"contact {EMAIL}"))

    def test_ip_addresses(self):
        self.assertEqual(kinds("x.md", "proxy 203.0.113.7, test 198.51.100.2, local 127.0.0.1"), [])
        public_ip = ".".join(["8"] * 4)
        self.assertIn(f"real-looking IP address {public_ip}", kinds("x.md", f"dns {public_ip}"))
        self.assertEqual(kinds("x.md", "opencv-python version 4.10.0.84"), [])   # a version
        self.assertEqual(kinds("x.md", "999.300.1.1 isn't an address"), [])

    def test_forbidden_files(self):
        found = {f.kind for f in scan.scan_paths(["templates/my_screen.png", "targets.json", ".env"])}
        self.assertTrue(any("templates/" in k for k in found))
        self.assertTrue(any("targets.json" in k for k in found))
        self.assertTrue(any(".env" in k for k in found))
        self.assertEqual(scan.scan_paths(["templates/.gitkeep", "docs/images/pathlab.png"]), [])

    def test_whole_run_on_a_temporary_repo_with_planted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "ok.py").write_text("import json\n", encoding="utf-8")
            (root / "src" / "bad.py").write_text(f"{EV}(input())\n", encoding="utf-8")
            files = ["src/ok.py", "src/bad.py"]
            with mock.patch.object(scan, "ROOT", root), mock.patch.object(scan, "tracked_files", return_value=files):
                self.assertEqual(scan.main(["--offline"]), 1)
                (root / "src" / "bad.py").write_text("print('fixed')\n", encoding="utf-8")
                self.assertEqual(scan.main(["--offline"]), 0)


if __name__ == "__main__":
    unittest.main()
