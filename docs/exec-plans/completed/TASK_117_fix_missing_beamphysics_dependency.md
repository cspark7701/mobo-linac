# TASK_117: Fix Missing 'beamphysics' Module on New Machines

## 1. Issue Description
On a new machine or fresh environment setup, the user encountered:
```text
ModuleNotFoundError: No module named 'beamphysics'
```

## 2. Root Cause
- The Python package that provides the `import beamphysics` module is **`openpmd-beamphysics`** (developed by Christopher Mayes for openPMD particle beam data).
- While `distgen` and `lume-astra` depend on it, on some pip/conda versions or fresh manual clone installations, `openpmd-beamphysics` was not explicitly listed in [`pyproject.toml`](file:///home/cspark/Work/projects/mobo-linac/pyproject.toml), [`INSTALL.md`](file:///home/cspark/Work/projects/mobo-linac/INSTALL.md), or [`install.sh`](file:///home/cspark/Work/projects/mobo-linac/install.sh).

## 3. Resolution
1. **Repository Dependencies (`pyproject.toml`)**:
   Added `"openpmd-beamphysics>=0.8.0"` explicitly to `dependencies`:
   ```toml
   dependencies = [
       ...
       "openpmd-beamphysics>=0.8.0",
       "distgen @ git+https://github.com/ColwynGulliford/distgen.git",
       "lume-astra @ git+https://github.com/ChristopherMayes/lume-astra.git",
   ]
   ```
2. **Automated Setup (`install.sh`)**:
   Added `python -m pip install openpmd-beamphysics` to the dependency setup step.
3. **Installation Guide (`INSTALL.md`)**:
   Updated Step 4 to explicitly list `pip install openpmd-beamphysics`.

## 4. Fix for Other Machines
To resolve the error on any other machine:
```bash
conda activate linac-opt
pip install openpmd-beamphysics
# Or reinstall project dependencies:
pip install -e .
```
