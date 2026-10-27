# Task Execution Summary: TASK_87 — CLI Batch Size Flag Options Across All Subcommands

## 1. Overview & Objectives
- **Goal**: Enable full alias support for batch size (`-b`, `-q`, `--batch-size`, `--batch_size`) across all `mobo-linac` CLI subcommands, particularly ensuring `mobo-linac resume` allows custom batch size overrides for subsequent iterations.

---

## 2. Work Implemented

### 2.1 CLI Argument Parser Updates ([`src/mobo_linac/cli.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/cli.py))
- Updated `add_common_run_args()`, `resume_parser`, and `run_bm_parser` to accept all standard batch size flags:
  ```python
  subparser.add_argument(
      "-b", "-q", "--batch-size", "--batch_size",
      dest="batch_size",
      type=int,
      help="Batch size for candidate proposals"
  )
  ```
- In `resume_optimization()`, correctly applied batch size override when supplied:
  ```python
  batch_size = getattr(args, "batch_size", None) or ckpt_data.get("batch_size", 4)
  ```

---

## 3. Verification Results

```bash
mobo-linac resume --help
mobo-linac run-constrained --help
pytest tests/test_cli.py -v
```
**Output:**
```
========================= 3 passed in 67.45s (0:01:07) =========================
```

---

## 4. Key Files Modified
- `src/mobo_linac/cli.py`
