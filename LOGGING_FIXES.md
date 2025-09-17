# Logging and Placeholder Fixes for Cosmos Workflow

## Issue Summary
The queue service logging is not properly formatting placeholders, resulting in log entries like "Failed job %s: %s" instead of showing actual job IDs and error messages. Additionally, Docker logs are not being properly downloaded for failed runs.

## Implementation Status
✅ **COMPLETED** - All logging fixes have been implemented as of 2025-09-17

## 1. Queue Service Logging Placeholder Fixes ✅

### File: `cosmos_workflow/services/queue_service.py`

**Status: Already Fixed** - All logging statements in queue_service.py were found to already have proper parameters.
The placeholders are correctly formatted with parameters passed.

## 2. Docker Log Download Issues ✅

### Problem
When Docker containers fail with exit code 125 (Docker daemon errors), the run logs are not being downloaded properly. Only the initial startup logs are captured before the container fails.

### Solution Implemented
Added `_create_fallback_log()` method to `docker_executor.py` that creates log files when Docker fails to start.

#### Implementation Details:
1. **Fallback Log Method** - Creates logs at correct path: `/outputs/run_{run_id}/logs/{run_id}.log`
2. **Integrated with all operations**:
   - Inference operations (line 473-479)
   - Upscaling operations (line 554-560)
   - Enhancement operations (line 398-404)
3. **Log Content Includes**:
   - Timestamp
   - Exit code
   - Error message
   - Docker stderr output

## 3. Additional Logging Improvements ✅

### Docker Command Logging - IMPLEMENTED
Added debug logging for all Docker commands before execution:
- Inference operations (line 418)
- Upscaling operations (line 490)
- Enhancement operations (line 339)
- Batch inference operations (line 812)

Example:
```python
logger.debug("Executing Docker command for inference: %s", command)
```

### Exit Code Context - IMPLEMENTED
Exit codes are now logged with failures and included in fallback logs

## 4. What These Fixes Achieve

1. **Better Debugging** - Docker commands are logged at debug level for troubleshooting
2. **Never Missing Logs** - Fallback logs ensure you always have error information, even when Docker fails to start
3. **Correct Log Paths** - Logs are created at the expected location: `/outputs/run_{run_id}/logs/{run_id}.log`
4. **Complete Error Context** - Exit codes, timestamps, and stderr are captured

## 5. Testing the Fixes

To verify these fixes work:

1. **Enable debug logging** to see Docker commands:
   ```bash
   export LOG_LEVEL=DEBUG
   cosmos inference ps_xxxxx
   ```

2. **Test with a working job** - Should see Docker command in debug logs

3. **Test with Docker failure** - Should create fallback log with error details

## Notes

- The logging uses parameterized formatting (e.g., `%s`) which is the correct approach for Python logging
- Never use f-strings or `.format()` with logger calls as they evaluate even when logging is disabled
- The exit code 125 specifically indicates Docker daemon issues, not application failures
- Fallback logs ensure debugging information is always available