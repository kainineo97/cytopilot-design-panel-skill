from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "design_panel.py"


class DesignPanelSmokeTest(unittest.TestCase):
    def test_synthetic_example_runs(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--request",
                str(ROOT / "examples" / "request.synthetic.json"),
                "--catalog",
                str(ROOT / "examples" / "catalog.synthetic.json"),
                "--spectra",
                str(ROOT / "examples" / "spectra.synthetic.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(len(result["assignments"]), 3)
        self.assertEqual(len({item["detector"] for item in result["assignments"]}), 3)
        self.assertEqual(result["unresolved_markers"], [])

    def test_json_spectra_parser_rejects_empty_input(self) -> None:
        spec = importlib.util.spec_from_file_location("design_panel", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(module.InputError):
            module.parse_spectra(ROOT / "examples" / "request.synthetic.json")


if __name__ == "__main__":
    unittest.main()
