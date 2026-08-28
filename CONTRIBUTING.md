# Contributing

By submitting a contribution, you agree that it may be distributed under this repository's MIT License and that you have the right to contribute it.

Do not commit real patient/sample data, laboratory inventory exports, credentials, proprietary manufacturer datasets, or copied prompts/templates without documented redistribution rights. Use synthetic fixtures in tests.

Before opening a pull request:

```bash
python -m unittest discover -s tests -v
python scripts/design_panel.py --request examples/request.synthetic.json --catalog examples/catalog.synthetic.json --spectra examples/spectra.synthetic.json --pretty
```

Explain any change to scoring thresholds or safety language and provide evidence that it does not convert heuristic overlap into an empirical compensation claim.
