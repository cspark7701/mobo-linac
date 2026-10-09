"""Proposal strategies independent of simulator initialization and run storage."""
from dataclasses import dataclass
from mobo_linac.config import MoboConfig
import torch
from botorch.models import ModelListGP
from mobo_linac.acquisition.mobo import SliceObjective
from mobo_linac.constraints import get_botorch_constraint_functions
from mobo_linac.metrics.hypervolume import compute_reference_point


@dataclass
class ProposalContext:
    config: MoboConfig
    device: torch.device
    scalar_weights: torch.Tensor
    constrained: bool
    acq_type: str


def propose_scalarized(context, training, bounds, schema, iteration, proposal_batch_size, sobol_engine, persist_model, dependencies):
    train_X, train_Y, train_feas_mask = training.train_X, training.train_Y, training.feasible
    build_scalarized_gp_model = dependencies["build_scalarized_gp_model"]
    fit_gp_models = dependencies["fit_gp_models"]
    qLogNoisyExpectedImprovement = dependencies["qLogNoisyExpectedImprovement"]
    generate_next_candidates = dependencies["generate_next_candidates"]
    # Scalarized single-objective GP surrogate with qLogNEI
    weights_dev = context.scalar_weights.to(dtype=torch.double, device=context.device)
    train_X_dev = train_X.to(dtype=torch.double, device=context.device)
    train_Y_dev = train_Y.to(dtype=torch.double, device=context.device)
    # Configured scales make objective weights dimensionless.
    scales_dev = torch.tensor(schema.scales, dtype=torch.double, device=context.device)
    train_Y_scaled = train_Y_dev / scales_dev
    scalar_Y = (train_Y_scaled * weights_dev).sum(dim=-1, keepdim=True)

    bounds_dev = bounds.to(device=context.device, dtype=torch.double)
    gp = build_scalarized_gp_model(
        train_X=train_X_dev,
        train_Y=scalar_Y,
        bounds=bounds_dev,
        covar_type=context.config.model.covar_type,
        noise_mode=context.config.model.noise_mode,
        fixed_noise_val=context.config.model.fixed_noise_variance,
        relative_noise_ratio=context.config.model.relative_noise_ratio,
        min_noise_variance=context.config.model.min_noise_variance,
        device=context.device,
    )
    fit_gp_models(gp)
    persist_model(gp, iteration, training)

    if context.device.type == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()

    acq_func = qLogNoisyExpectedImprovement(
        model=gp,
        X_baseline=train_X_dev,
        prune_baseline=True,
    )
    exec_cfg = context.config.execution
    b_limit = 1 if context.device.type == "cuda" else getattr(exec_cfg, "acqf_batch_limit", 5)
    proposal_result = generate_next_candidates(
        acq_func=acq_func,
        bounds=bounds_dev,
        batch_size=proposal_batch_size,
        num_restarts=getattr(exec_cfg, "acqf_num_restarts", 10),
        raw_samples=getattr(exec_cfg, "acqf_raw_samples", 1024),
        maxiter=getattr(exec_cfg, "acqf_maxiter", 200),
        batch_limit=b_limit,
        device=context.device,
        sobol_engine=sobol_engine,
    )
    candidates, _ = proposal_result
    proposal_metadata = getattr(proposal_result, "metadata", None)
    next_cand_list = candidates.detach().cpu().tolist()

    return next_cand_list, proposal_metadata


def propose_multiobjective(context, training, bounds, schema, iteration, proposal_batch_size, sobol_engine, persist_model, dependencies):
    train_X, train_Y, train_feas_mask = training.train_X, training.train_Y, training.feasible
    SurrogatePipeline = dependencies["SurrogatePipeline"]
    build_acquisition_function = dependencies["build_acquisition_function"]
    generate_next_candidates = dependencies["generate_next_candidates"]
    pipeline = SurrogatePipeline(
        bounds=bounds,
        covar_type=context.config.model.covar_type,
        noise_mode=context.config.model.noise_mode,
        fixed_noise_val=context.config.model.fixed_noise_variance,
        relative_noise_ratio=context.config.model.relative_noise_ratio,
        min_noise_variance=context.config.model.min_noise_variance,
        objective_noise_variances=context.config.model.objective_noise_variances,
        constraints_config=context.config.constraints,
        device=context.device,
    )

    if context.constrained:
        pipeline.fit(train_X, train_Y, training.constraints)
        if pipeline.constraint_model is not None:
            gp_model = ModelListGP(*pipeline.objective_model.models, *pipeline.constraint_model.models).to(device=context.device, dtype=torch.double)
            botorch_constraints = get_botorch_constraint_functions(context.config, num_objectives=train_Y.shape[-1])
            objective_slice = SliceObjective(num_objectives=train_Y.shape[-1])
        else:
            gp_model = pipeline.objective_model
            botorch_constraints = None
            objective_slice = None
    else:
        pipeline.fit(train_X, train_Y)
        gp_model = pipeline.objective_model
        botorch_constraints = None
        objective_slice = None

    persist_model(pipeline, iteration, training, pipeline=True)

    acq_ref_point = compute_reference_point(train_Y, offset_ratio=0.05, config=context.config)

    acq_func = build_acquisition_function(
        model=gp_model,
        train_X=train_X,
        train_Y=train_Y,
        ref_point=acq_ref_point,
        train_feas_mask=train_feas_mask,
        acq_type=context.acq_type,
        constraints=botorch_constraints,
        objective=objective_slice,
    )

    exec_cfg = context.config.execution
    proposal_result = generate_next_candidates(
        acq_func=acq_func,
        bounds=bounds,
        batch_size=proposal_batch_size,
        num_restarts=getattr(exec_cfg, "acqf_num_restarts", 10),
        raw_samples=getattr(exec_cfg, "acqf_raw_samples", 1024),
        maxiter=getattr(exec_cfg, "acqf_maxiter", 200),
        batch_limit=getattr(exec_cfg, "acqf_batch_limit", 5),
        device=context.device,
        sobol_engine=sobol_engine,
    )
    next_cand_tensor, _ = proposal_result
    proposal_metadata = getattr(proposal_result, "metadata", None)
    next_cand_list = next_cand_tensor.detach().cpu().tolist()

    return next_cand_list, proposal_metadata
