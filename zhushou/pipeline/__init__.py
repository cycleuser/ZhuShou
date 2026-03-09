"""ZhuShou autonomous coding pipeline.

The pipeline runner (``PipelineRunner``) executes an 8/10-stage coding
pipeline for a single task.  The top-level orchestrator dispatches
multiple runners concurrently.
"""

from zhushou.pipeline.runner import PipelineRunner

# Backward compatibility: existing imports of PipelineOrchestrator still work.
PipelineOrchestrator = PipelineRunner

__all__ = ["PipelineRunner", "PipelineOrchestrator"]
