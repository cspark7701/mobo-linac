"""
Surrogate Pipeline Module for mobo_linac.

Encapsulates Gaussian Process surrogate model building, fitting, prediction,
and constraint feasibility modeling in a clean, unified interface.
"""

from typing import Dict, List, Optional, Tuple, Union
import torch
from torch import Tensor
from botorch.models import ModelListGP

from mobo_linac.models.gp import build_gp_models, fit_gp_models


class SurrogatePipeline:
    """
    Unified manager for objective and constraint GP surrogate models.
    """

    def __init__(
        self,
        bounds: Tensor,
        covar_type: str = "matern52",
        noise_mode: str = "deterministic_fixed",
        fixed_noise_val: float = 1e-6,
        objective_noise_variances: Optional[List[float]] = None,
        device: Optional[Union[str, torch.device]] = None,
    ):
        from mobo_linac.utils import get_device
        self.device = get_device(device if isinstance(device, str) else (str(device) if device is not None else None))

        self.bounds = bounds.to(dtype=torch.double, device=self.device)
        self.covar_type = covar_type
        self.noise_mode = noise_mode
        self.fixed_noise_val = fixed_noise_val
        self.objective_noise_variances = objective_noise_variances
        self.objective_model: Optional[ModelListGP] = None
        self.constraint_model: Optional[ModelListGP] = None
        self.is_fitted: bool = False

    def fit(
        self,
        train_X: Tensor,
        train_Y: Tensor,
        train_constraints: Optional[Tensor] = None,
        train_Yvar: Optional[Tensor] = None,
    ) -> "SurrogatePipeline":
        """
        Fits GP models for both objectives and optional constraint metrics.

        Args:
            train_X: (N, D) PyTorch double tensor of design variables.
            train_Y: (N, M) PyTorch double tensor of model-space objectives.
            train_constraints: Optional (N, K) PyTorch double tensor of constraint metrics.
            train_Yvar: Optional (N, M) PyTorch double tensor of observation noise variances.

        Returns:
            Fitted SurrogatePipeline instance.
        """
        if train_X.shape[0] < 2:
            raise ValueError("Cannot fit SurrogatePipeline with fewer than 2 data points.")

        train_X_dbl = train_X.to(dtype=torch.double, device=self.device)
        train_Y_dbl = train_Y.to(dtype=torch.double, device=self.device)

        # Fit objective surrogates
        self.objective_model = build_gp_models(
            train_X=train_X_dbl,
            train_Y=train_Y_dbl,
            bounds=self.bounds,
            covar_type=self.covar_type,
            noise_mode=self.noise_mode,
            fixed_noise_val=self.fixed_noise_val,
            objective_noise_variances=self.objective_noise_variances,
            train_Yvar=train_Yvar.to(dtype=torch.double, device=self.device) if train_Yvar is not None else None,
            device=self.device,
        )
        self.objective_model = fit_gp_models(self.objective_model)

        # Fit constraint surrogates if provided
        if train_constraints is not None and train_constraints.numel() > 0:
            c_dbl = train_constraints.to(dtype=torch.double, device=self.device)
            self.constraint_model = build_gp_models(
                train_X=train_X_dbl,
                train_Y=c_dbl,
                bounds=self.bounds,
                covar_type=self.covar_type,
                noise_mode=self.noise_mode,
                fixed_noise_val=self.fixed_noise_val,
                device=self.device,
            )
            self.constraint_model = fit_gp_models(self.constraint_model)
        else:
            self.constraint_model = None

        self.is_fitted = True
        return self


    def predict_objectives(self, X: Tensor) -> Tuple[Tensor, Tensor]:
        """
        Predicts mean and variance for objective functions at candidate inputs X.

        Args:
            X: (..., D) PyTorch tensor.

        Returns:
            Tuple of (mean, variance) Tensors.
        """
        if not self.is_fitted or self.objective_model is None:
            raise RuntimeError("SurrogatePipeline must be fitted before predicting.")

        X_dbl = X.to(dtype=torch.double, device=self.device)
        posterior = self.objective_model.posterior(X_dbl)
        return posterior.mean, posterior.variance

    def predict_probability_of_feasibility(self, X: Tensor) -> Tensor:
        """
        Computes predictive probability of feasibility P(c_i(x) <= 0 for all i) at candidate points X.

        Args:
            X: (..., D) PyTorch tensor.

        Returns:
            Tensor of probability values in [0, 1].
        """
        if not self.is_fitted:
            raise RuntimeError("SurrogatePipeline must be fitted before predicting feasibility.")

        X_dbl = X.to(dtype=torch.double, device=self.device)

        if self.constraint_model is None:
            return torch.ones(X_dbl.shape[:-1], dtype=torch.double, device=self.device)

        posterior = self.constraint_model.posterior(X_dbl)
        mean = posterior.mean
        sigma = posterior.variance.sqrt().clamp(min=1e-9)

        normal_dist = torch.distributions.Normal(0.0, 1.0)
        prob_per_constraint = normal_dist.cdf(-mean / sigma)

        total_prob = prob_per_constraint.prod(dim=-1)
        return total_prob
