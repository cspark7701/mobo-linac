"""Audit exact attempt provenance independently of comparison and report generation."""
from pathlib import Path

from mobo_linac.result_schema import ResultSchema
from mobo_linac.diagnostics import diagnostic_observations
from mobo_linac.astra.workdir import file_sha256, read_evaluation_manifest
from mobo_linac.status import is_success


def audit_attempt(result, required=False, *, config):
    record = {"run_id": result.run_id, "evaluation_id": result.evaluation_id,
              "attempt_id": result.attempt_id, "manifest_path": result.manifest_path,
              "input_sha256": None, "input_hashes": {}, "executable_sha256": None,
              "audit_status": "UNKNOWN", "issues": []}
    path = Path(result.manifest_path) if result.manifest_path else Path(result.work_dir) / "manifest.json"
    if not result.manifest_path and not result.work_dir:
        record["issues"].append("No original attempt provenance available" if not required else "Missing rerun manifest")
        return record
    modern_manifest = False
    try:
        manifest = read_evaluation_manifest(path)
        modern_manifest = manifest.get("schema_version", 0) == 1
        hashes = manifest.get("input_hashes", {})
        record.update(input_hashes=hashes, input_sha256=hashes.get("astra.in"),
                      executable_sha256=manifest.get("executable", {}).get("sha256"))
        if manifest.get("schema_version", 0) == 0 and not required:
            record["issues"].append("Legacy manifest lacks retained attempt hash evidence")
            return record
        if manifest.get("run_id") != result.run_id or manifest.get("eval_id") != result.evaluation_id:
            record["issues"].append("Manifest evaluation identity mismatch")
        if result.attempt_id is not None and manifest.get("attempt_id") != result.attempt_id:
            record["issues"].append("Manifest attempt identity mismatch")
        if not hashes or "astra.in" not in hashes:
            record["issues"].append("Missing effective input hashes")
        for name, digest in hashes.items():
            snapshot = (path.parent / "inputs" / name).resolve()
            snapshot.relative_to((path.parent / "inputs").resolve())
            if file_sha256(snapshot) != digest:
                record["issues"].append(f"Input snapshot checksum mismatch: {name}")
        after = manifest.get("input_hashes_after_execution", {})
        if after != hashes:
            record["issues"].append("Input state changed during execution or lacks final input evidence")
        for name, digest in after.items():
            snapshot = (path.parent / "inputs_after_execution" / name).resolve()
            snapshot.relative_to((path.parent / "inputs_after_execution").resolve())
            if file_sha256(snapshot) != digest:
                record["issues"].append(f"Final input snapshot checksum mismatch: {name}")
        schema = ResultSchema.from_config(config)
        if schema.extract(manifest.get("objectives")) != schema.extract(result.objectives_physical):
            record["issues"].append("Manifest objective observations mismatch")
        if diagnostic_observations(manifest.get("diagnostics") or {}) != diagnostic_observations(result.diagnostics):
            record["issues"].append("Manifest diagnostic observations mismatch")
        binary = manifest.get("executable", {})
        if not binary.get("path") or not record["executable_sha256"]:
            record["issues"].append("Missing executable provenance")
        elif file_sha256(binary["path"]) != record["executable_sha256"]:
            record["issues"].append("Executable checksum mismatch")
        if manifest.get("parameters") != result.x_physical:
            record["issues"].append("Manifest parameters mismatch")
        if not is_success(manifest.get("status")):
            record["issues"].append("Attempt manifest does not record success")
        record["audit_status"] = "FAILED" if record["issues"] else "VERIFIED"
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        record["issues"].append(str(exc))
        record["audit_status"] = "FAILED" if required or modern_manifest else "UNKNOWN"
    return record
