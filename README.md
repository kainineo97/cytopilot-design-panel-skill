# CytoPilot Panel Design Skill

An MIT-licensed Codex skill for designing and reviewing conventional flow-cytometry antibody panels from a user-supplied reagent catalog, instrument configuration, and approximate fluorophore spectra.

The repository contains the complete skill, a standard-library-only ranking script, synthetic examples, and smoke tests. It does **not** contain a real laboratory inventory, manufacturer catalog export, empirical spillover matrix, or patient/sample data.

## Install as a Codex skill

Copy or clone this repository into your Codex skills directory so that `SKILL.md` is at the skill root. Restart or refresh Codex skill discovery if needed.

## Standalone smoke test

Python 3.10 or newer is recommended. No third-party Python packages are required.

```bash
python scripts/design_panel.py \
  --request examples/request.synthetic.json \
  --catalog examples/catalog.synthetic.json \
  --spectra examples/spectra.synthetic.json \
  --pretty
python -m unittest discover -s tests -v
```

The example records and optical values are deliberately synthetic and exist only to exercise the file contract. Replace them with reviewed local data before real panel work.

## Input boundaries

- A catalog record is not evidence of physical stock.
- Approximate spectra rank review priority; they are not compensation coefficients.
- Same-detector assignments are infeasible on a conventional detector and must be reassigned.
- Final panels require reagent verification, titration, matched single-stain controls, and biological review.

## Repository layout

- `SKILL.md`: agent instructions and safety boundaries.
- `agents/openai.yaml`: display metadata.
- `references/`: input/output contract and panel rules.
- `scripts/design_panel.py`: deterministic ranking helper.
- `examples/`: synthetic, non-clinical smoke-test inputs.
- `tests/`: standard-library tests.

## Licensing and provenance

Project-authored code and documentation are released under the [MIT License](LICENSE). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for named formats, products, and the pre-publication provenance checklist.

Before publishing under a personal or institutional account, replace “CytoPilot contributors” in `LICENSE` if a different legal copyright holder is required.

## 中文说明

本仓库是可独立安装的 CytoPilot Panel 设计 skill。示例目录、抗体记录与光谱参数均为合成测试数据，不代表真实库存、厂家产品或实验补偿矩阵。真实使用前必须替换为经过审核的本地数据，并完成滴定、单染和人工生物学复核。
