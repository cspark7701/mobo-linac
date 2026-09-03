"""
Shared configuration, labels, scales, and saving helpers for mobo_linac plotting.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union

import matplotlib.pyplot as plt

# Shared unit conversion constants
EMIT_SCALE = 1e6      # m·rad -> mm·mrad (or um·rad)
ENERGY_SCALE = 1e-6   # eV -> MeV

# LaTeX-formatted design variable labels
DESIGN_VAR_LABELS = [
    r"$B_\mathrm{sol}$ [T]",
    r"$G_{q1}$ [T/m]",
    r"$G_{q2}$ [T/m]",
    r"$\phi_\mathrm{gun}$ [°]",
    r"$\phi_\mathrm{acc1/2}$ [°]",
    r"$\phi_\mathrm{acc3/4}$ [°]",
]

# Short design variable labels
DESIGN_VAR_SHORT_LABELS = [
    r"$B_{sol}$",
    r"$G_{q1}$",
    r"$G_{q2}$",
    r"$\phi_{gun}$",
    r"$\phi_{12}$",
    r"$\phi_{34}$",
]

# Objective labels
OBJ_LABELS = [
    r"$\varepsilon_{n,x}$ [mm·mrad]",
    r"$\varepsilon_{n,y}$ [mm·mrad]",
    r"$\sigma_E$ [MeV]",
]


@contextmanager
def figure_scope(auto_close: bool = True) -> Generator[None, None, None]:
    """
    Context manager that automatically tracks and closes all Matplotlib figures
    created within its scope upon exit, preventing memory accumulation.
    """
    initial_fignums = set(plt.get_fignums())
    try:
        yield
    finally:
        if auto_close:
            current_fignums = set(plt.get_fignums())
            new_fignums = current_fignums - initial_fignums
            for fignum in new_fignums:
                plt.close(fignum)


def close_all_figures() -> None:
    """Closes all currently open Matplotlib figures."""
    plt.close("all")


def save_fig(
    fig: plt.Figure,
    output_path: Optional[Union[str, Path]],
    dpi: int = 300,
    close: bool = False,
) -> None:
    """Saves figure to disk if output_path is provided, creating parent directories and optionally closing it."""
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    if close:
        plt.close(fig)


# Alias for backward compatibility
_save = save_fig
_EMIT_SCALE = EMIT_SCALE
_ENERGY_SCALE = ENERGY_SCALE
_DESIGN_VAR_LABELS = DESIGN_VAR_LABELS
_OBJ_LABELS = OBJ_LABELS
