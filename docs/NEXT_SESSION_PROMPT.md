# Manual Testing - Post Checkpoint Installation

## Status
✅ **Auto-streaming UI complete** - Ready for testing once checkpoints installed
❌ **Checkpoints missing** - User downloading AI model checkpoints

## Quick Testing Steps

1. **Test CLI**: `cosmos inference ps_4943750370622cfefc54`
   - Should run several minutes (not seconds)
   - Should show actual AI inference progress

2. **Test UI**: `cosmos ui --port 8001` → http://localhost:8001
   - Auto-detects running jobs
   - Streams logs in real-time with color coding

3. **Test Integration**: Start job via CLI, UI should auto-switch to stream it

## Docker Log Access Tips

```bash
# Connect to remote
./ssh_lambda.sh

# View running containers
sudo docker ps

# View live container logs
sudo docker logs -f <container_name>

# Execute commands inside container
sudo docker exec -it <container_name> /bin/bash

# Check GPU usage
nvidia-smi
```

## Known Issues (Non-blocking)
- Status reporting bug: Failed runs marked as "completed success"
- Container detection bug: `cosmos status --stream` doesn't work (use UI instead)

## Success Indicators
- Jobs run >60 seconds (real AI work, not quick failures)
- No FileNotFoundError for model checkpoints
- UI auto-detects jobs and streams logs
- Logs show actual inference progress

See `docs/logging-infrastructure-implementation-plan.md` for complete details.