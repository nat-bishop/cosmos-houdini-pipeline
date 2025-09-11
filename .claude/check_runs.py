"""Check run statuses directly."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.api.cosmos_api import CosmosAPI

# Initialize API
ops = CosmosAPI()

# Get runs
runs = ops.list_runs(limit=5)

print(f"Found {len(runs)} runs:")
for run in runs:
    print(f"  - ID: {run['id'][:20]}... Status: {run.get('status', 'unknown')}")

# Try with status filter
completed_runs = ops.list_runs(status="completed", limit=5)
print(f"\nFound {len(completed_runs)} completed runs")

# Try with "all" to see what we get
all_runs = ops.list_runs(status=None, limit=5)
print(f"Found {len(all_runs)} runs with status=None")