"""Smart batching utilities for optimizing job queue execution.

Provides algorithms for grouping runs into efficient batches to reduce
GPU processing overhead and improve throughput.
"""

import json
from typing import TYPE_CHECKING, Any

from cosmos_workflow.utils.logging import logger

if TYPE_CHECKING:
    from cosmos_workflow.database.models import JobQueue


def get_control_signature(config: dict[str, Any]) -> tuple[str, ...]:
    """Extract sorted tuple of active controls from job config.

    Args:
        config: Job configuration dictionary with optional 'weights' field

    Returns:
        Sorted tuple of control names with weight > 0
    """
    weights = config.get("weights", {})
    active_controls = [control for control, weight in weights.items() if weight > 0]
    return tuple(sorted(active_controls))


def get_execution_signature(config: dict[str, Any]) -> str:
    """Create hashable signature from execution params (excluding weights).

    All parameters except weights must match for runs to be batchable.

    Args:
        config: Job configuration dictionary

    Returns:
        JSON string of execution parameters
    """
    # Extract all non-weight params that must match
    exec_params = {k: v for k, v in config.items() if k not in ["weights", "weights_list"]}

    # Add defaults for consistency
    exec_params.setdefault("num_steps", 25)
    exec_params.setdefault("guidance_scale", 5.0)
    exec_params.setdefault("seed", 1)

    return json.dumps(exec_params, sort_keys=True)


def group_runs_strict(jobs: list["JobQueue"], max_batch_size: int) -> list[dict[str, Any]]:
    """Group runs with identical control signatures AND execution params.

    Strict mode ensures homogeneous batches for fastest execution.

    Args:
        jobs: List of job objects to group
        max_batch_size: Maximum number of runs per batch

    Returns:
        List of batch configurations
    """
    if not jobs:
        return []

    groups = {}

    for job in jobs:
        # Must match both execution params and control types
        exec_sig = get_execution_signature(job.config)
        control_sig = get_control_signature(job.config)
        group_key = (exec_sig, control_sig)

        if group_key not in groups:
            groups[group_key] = []

        # Extract individual runs with their source
        for prompt_id in job.prompt_ids:
            groups[group_key].append(
                {
                    "prompt_id": prompt_id,
                    "weights": job.config.get("weights", {}),
                    "source_job_id": job.id,
                    "exec_params": job.config,
                }
            )

        logger.debug(
            "Job %s with %d runs -> strict group %s", job.id, len(job.prompt_ids), control_sig
        )

    # Log grouping results
    logger.info("Strict grouping: %d groups from %d jobs", len(groups), len(jobs))
    for (_exec_sig, control_sig), runs in groups.items():
        logger.debug("  Group %s: %d runs", control_sig, len(runs))

    return _create_batches_from_groups(groups, max_batch_size, "strict")


def group_runs_mixed(jobs: list["JobQueue"], max_batch_size: int) -> list[dict[str, Any]]:
    """Group runs by execution params only, allowing mixed control types.

    Mixed mode creates fewer batches but may run slower due to control overhead.

    Args:
        jobs: List of job objects to group
        max_batch_size: Maximum number of runs per batch

    Returns:
        List of batch configurations
    """
    if not jobs:
        return []

    groups = {}

    for job in jobs:
        # Only group by execution params, not control types
        exec_sig = get_execution_signature(job.config)

        if exec_sig not in groups:
            groups[exec_sig] = []

        # Extract individual runs
        for prompt_id in job.prompt_ids:
            groups[exec_sig].append(
                {
                    "prompt_id": prompt_id,
                    "weights": job.config.get("weights", {}),
                    "source_job_id": job.id,
                    "exec_params": job.config,
                }
            )

        control_sig = get_control_signature(job.config)
        logger.debug(
            "Job %s with %d runs -> mixed group (controls: %s)",
            job.id,
            len(job.prompt_ids),
            control_sig,
        )

    # Log grouping results
    logger.info("Mixed grouping: %d groups from %d jobs", len(groups), len(jobs))
    for _exec_sig, runs in groups.items():
        # Count unique control combinations
        control_sigs = set()
        for run in runs:
            control_sigs.add(tuple(sorted(run["weights"].keys())))
        logger.debug(
            "  Group with %d runs, %d unique control signatures", len(runs), len(control_sigs)
        )

    return _create_batches_from_groups(groups, max_batch_size, "mixed")


def _create_batches_from_groups(
    groups: dict[Any, list[dict[str, Any]]], max_batch_size: int, mode: str
) -> list[dict[str, Any]]:
    """Convert grouped runs into batch configurations.

    Args:
        groups: Dictionary mapping group keys to lists of runs
        max_batch_size: Maximum number of runs per batch
        mode: "strict" or "mixed" for logging

    Returns:
        List of batch configurations
    """
    batches = []

    for group_key, runs in groups.items():
        # Log group info
        if isinstance(group_key, tuple) and len(group_key) == 2:
            _, control_sig = group_key
            logger.info(
                "%s mode: creating batches for %d runs with controls %s",
                mode.capitalize(),
                len(runs),
                control_sig,
            )
        else:
            logger.info(
                "%s mode: creating batches for %d runs with mixed controls",
                mode.capitalize(),
                len(runs),
            )

        # Split into batches respecting max_batch_size
        for i in range(0, len(runs), max_batch_size):
            batch_runs = runs[i : i + max_batch_size]

            # Extract exec params from first run (all same in group)
            base_config = batch_runs[0]["exec_params"].copy()

            # Replace weights with weights_list
            base_config.pop("weights", None)
            base_config["weights_list"] = [r["weights"] for r in batch_runs]

            batches.append(
                {
                    "prompt_ids": [r["prompt_id"] for r in batch_runs],
                    "config": base_config,
                    "source_job_ids": list(set(r["source_job_id"] for r in batch_runs)),
                    "mode": mode,
                }
            )

            # Log batch details
            control_types = set()
            for r in batch_runs:
                control_types.update(r["weights"].keys())
            logger.debug(
                "  Batch %d: %d runs, %d source jobs, controls: %s",
                len(batches),
                len(batch_runs),
                len(set(r["source_job_id"] for r in batch_runs)),
                control_types if control_types else "none",
            )

    return batches


def calculate_batch_efficiency(
    batches: list[dict[str, Any]], original_jobs: list["JobQueue"], mode: str = "strict"
) -> dict[str, Any]:
    """Calculate efficiency metrics for batch configuration.

    Args:
        batches: List of batch configurations
        original_jobs: Original list of jobs before batching
        mode: "strict" or "mixed" for overhead calculation

    Returns:
        Dictionary with efficiency metrics
    """
    # Count total runs (not jobs!)
    total_runs = sum(len(job.prompt_ids) for job in original_jobs)
    total_batches = len(batches)
    original_job_count = len(original_jobs)

    if total_batches == 0:
        return {
            "total_runs": total_runs,
            "original_jobs": original_job_count,
            "total_batches": 0,
            "speedup": 1.0,
            "mode": mode,
        }

    # Base speedup from batching runs
    base_speedup = total_runs / total_batches

    # Adjust for mixed mode overhead
    if mode == "mixed":
        # Calculate overhead from control diversity
        total_overhead = 0
        for batch in batches:
            weights_list = batch["config"].get("weights_list", [])
            unique_controls = set()
            for weights in weights_list:
                unique_controls.update(weights.keys())

            # More diverse controls = more overhead
            num_controls = len(unique_controls)
            if num_controls > 2:
                # Each additional control adds ~10% overhead
                batch_overhead = 1 + (0.1 * (num_controls - 2))
                total_overhead += batch_overhead
            else:
                total_overhead += 1.0

        # Average overhead across batches
        avg_overhead = total_overhead / max(1, total_batches)
        adjusted_speedup = base_speedup / avg_overhead

        logger.info("Mixed mode overhead factor: %.2fx due to control diversity", avg_overhead)
    else:
        # Strict mode has minimal overhead
        adjusted_speedup = base_speedup * 0.95  # Small overhead for batching itself

    # Ensure reasonable bounds
    final_speedup = max(1.0, min(adjusted_speedup, total_runs))

    logger.info(
        "Efficiency: %d runs from %d jobs -> %d batches (%.1fx speedup, %s mode)",
        total_runs,
        original_job_count,
        total_batches,
        final_speedup,
        mode,
    )

    return {
        "total_runs": total_runs,
        "original_jobs": original_job_count,
        "total_batches": total_batches,
        "speedup": final_speedup,
        "mode": mode,
    }


def filter_batchable_jobs(jobs: list["JobQueue"]) -> list["JobQueue"]:
    """Filter jobs that can be batched together.

    Args:
        jobs: List of all jobs

    Returns:
        List of batchable jobs (inference and batch_inference only)
    """
    batchable_types = {"inference", "batch_inference"}
    batchable = [job for job in jobs if job.job_type in batchable_types]

    if len(batchable) < len(jobs):
        excluded = len(jobs) - len(batchable)
        logger.debug("Filtered out %d non-batchable jobs (enhancement/upscale)", excluded)

    return batchable
