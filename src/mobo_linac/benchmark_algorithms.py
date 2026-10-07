"""Explicit benchmark algorithm definitions, independent of simulator imports."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BenchmarkAlgorithm:
    optimization_mode: str
    acquisition: Optional[str]
    constrained: bool
    executor: Optional[str]


BENCHMARK_ALGORITHMS = {
    "constrained_qlognehvi": BenchmarkAlgorithm("constrained_mobo", "qLogNEHVI", True, "mobo"),
    "unconstrained_qlognehvi": BenchmarkAlgorithm("unconstrained_mobo", "qLogNEHVI", False, "mobo"),
    "qlogehvi": BenchmarkAlgorithm("unconstrained_mobo", "qLogEHVI", False, "mobo"),
    "scalarized_bo": BenchmarkAlgorithm("scalarized_bo", "qLogNEI", False, "mobo"),
    "nsga2": BenchmarkAlgorithm("nsga2", None, False, None),
    "sobol": BenchmarkAlgorithm("sobol", None, False, None),
}
SUPPORTED_BENCHMARK_ALGORITHMS = [
    name for name, spec in BENCHMARK_ALGORITHMS.items() if spec.executor is not None
]


def get_benchmark_algorithm(name: str) -> BenchmarkAlgorithm:
    if name not in BENCHMARK_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm '{name}'. Supported: {SUPPORTED_BENCHMARK_ALGORITHMS}")
    spec = BENCHMARK_ALGORITHMS[name]
    if spec.executor is None:
        raise ValueError(f"Benchmark algorithm '{name}' has no implemented executor. Supported: {SUPPORTED_BENCHMARK_ALGORITHMS}")
    return spec
