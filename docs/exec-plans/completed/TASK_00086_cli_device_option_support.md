# Task Execution Summary: TASK_85 — CLI `--device` Option Support Across Subcommands

## 1. Overview & Objectives
- **Goal**: Add `--device` option (`auto`, `cuda`, `cuda:0`, `cpu`) support across all `mobo-linac` CLI subcommands (`run-unconstrained`, `run-constrained`, `run-scalarized`, `run-validation`, `resume`, `run-benchmark`).

---

## 2. Work Implemented

### 2.1 CLI Argument Parser Updates ([`src/mobo_linac/cli.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/cli.py))
- Added `--device` to `add_common_run_args()`:
  ```python
  subparser.add_argument("--device", type=str, default="auto", help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')")
  ```
- Added `--device` and `-b` / `-q` / `--batch-size` to `resume_parser`.
- Added `--device` to `run_bm_parser`.
- Updated `run_unconstrained`, `run_constrained`, `run_validation`, `resume_optimization`, and `run-benchmark` command handlers to pass `device=getattr(args, "device", "auto")` to `MoboCampaignRunner` and `BenchmarkCampaignRunner`.

### 2.2 Benchmark Campaign Runner Updates ([`src/mobo_linac/campaigns/benchmark.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/campaigns/benchmark.py))
- Added `device: str = "auto"` parameter to `BenchmarkCampaignRunner.__init__` and passed `device=self.device` into `MoboCampaignRunner`.

---

## 3. Verification Results

```bash
mobo-linac resume --help
mobo-linac run-constrained --help
pytest tests/test_cli.py -v
```
**Output:**
```
========================= 3 passed in 67.28s (0:01:07) =========================
```

---

## 4. Key Files Modified
- `src/mobo_linac/cli.py`
- `src/mobo_linac/campaigns/benchmark.py`
