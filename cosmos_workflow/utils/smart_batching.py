"""Smart batching utilities for optimizing job queue execution.

Provides algorithms for grouping jobs into efficient batches to reduce
GPU processing overhead and improve throughput.
"""


def get_control_signature(job_config: dict) -> tuple[str, ...]:
    """Extract sorted tuple of active controls from job config.

    Args:
        job_config: Job configuration dictionary with optional 'weights' field

    Returns:
        Sorted tuple of control names with weight > 0
    """
    weights = job_config.get("weights", {})
    active_controls = [control for control, weight in weights.items() if weight > 0]
    return tuple(sorted(active_controls))


def group_jobs_strict(jobs: list, max_batch_size: int) -> list[dict]:
    """Group jobs with identical control signatures only.

    Args:
        jobs: List of job objects to group
        max_batch_size: Maximum number of jobs per batch

    Returns:
        List of batch configurations with 'jobs' and 'signature'
    """
    if not jobs:
        return []

    # Group jobs by signature
    signature_groups = {}
    for job in jobs:
        signature = get_control_signature(job.config)
        if signature not in signature_groups:
            signature_groups[signature] = []
        signature_groups[signature].append(job)

    # Split groups into batches respecting max_batch_size
    batches = []
    for signature, group_jobs in signature_groups.items():
        for i in range(0, len(group_jobs), max_batch_size):
            batch_jobs = group_jobs[i : i + max_batch_size]
            batches.append({"jobs": batch_jobs, "signature": signature})

    return batches


def group_jobs_mixed(jobs: list, max_batch_size: int) -> list[dict]:
    """Group jobs allowing mixed controls using master batch approach.

    Creates batches that minimize total control overhead by grouping
    jobs and using the union of all controls as master controls.

    Args:
        jobs: List of job objects to group
        max_batch_size: Maximum number of jobs per batch

    Returns:
        List of batch configurations with 'jobs' and 'master_controls'
    """
    if not jobs:
        return []

    batches = []
    remaining_jobs = list(jobs)

    while remaining_jobs:
        # Take up to max_batch_size jobs for this batch
        batch_jobs = remaining_jobs[:max_batch_size]
        remaining_jobs = remaining_jobs[max_batch_size:]

        # Calculate master controls (union of all controls in batch)
        master_controls = set()
        for job in batch_jobs:
            signature = get_control_signature(job.config)
            master_controls.update(signature)

        batches.append({"jobs": batch_jobs, "master_controls": list(master_controls)})

    return batches


def calculate_batch_efficiency(batches: list[dict], original_jobs: list) -> dict:
    """Calculate efficiency metrics for batch configuration.

    Args:
        batches: List of batch configurations
        original_jobs: Original list of jobs before batching

    Returns:
        Dictionary with efficiency metrics
    """
    job_count_before = len(original_jobs)
    job_count_after = len(batches)

    if job_count_after == 0:
        estimated_speedup = 1.0
    else:
        # Basic speedup calculation
        estimated_speedup = job_count_before / job_count_after

        # Adjust for control overhead in mixed batches
        total_control_overhead = 0
        for batch in batches:
            if "master_controls" in batch:
                # Mixed mode: penalty for more controls
                num_controls = len(batch["master_controls"])
                if num_controls > 2:
                    # Reduce speedup for many controls
                    overhead_factor = 1.0 + (num_controls - 2) * 0.1
                    total_control_overhead += overhead_factor

        if total_control_overhead > 0:
            # Average the overhead across batches
            avg_overhead = total_control_overhead / len(batches)
            estimated_speedup = estimated_speedup / avg_overhead
            # Ensure speedup is at least 1.5x for mixed mode
            estimated_speedup = max(1.5, min(estimated_speedup, 2.5))

    # Calculate control reduction
    original_control_count = sum(len(get_control_signature(job.config)) for job in original_jobs)

    batch_control_count = 0
    for batch in batches:
        if "signature" in batch:
            # Strict mode: same controls for all jobs
            batch_control_count += len(batch["signature"])
        elif "master_controls" in batch:
            # Mixed mode: master controls
            batch_control_count += len(batch["master_controls"])

    control_reduction = max(0, original_control_count - batch_control_count)

    return {
        "job_count_before": job_count_before,
        "job_count_after": job_count_after,
        "estimated_speedup": estimated_speedup,
        "control_reduction": control_reduction,
    }


def get_safe_batch_size(num_controls: int, user_max: int = 16) -> int:
    """Conservative batch sizing based on control count.

    Args:
        num_controls: Number of active controls
        user_max: User-specified maximum (default 16)

    Returns:
        Safe batch size considering memory constraints
    """
    if num_controls <= 1:
        safe_size = 8
    elif num_controls == 2:
        safe_size = 4
    else:  # 3 or more controls
        safe_size = 2

    return min(safe_size, user_max)


def filter_batchable_jobs(jobs: list) -> list:
    """Filter jobs that can be batched together.

    Args:
        jobs: List of all jobs

    Returns:
        List of batchable jobs (inference and batch_inference only)
    """
    batchable_types = {"inference", "batch_inference"}
    return [job for job in jobs if job.job_type in batchable_types]
