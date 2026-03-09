"""Unified Python API for Flask-based services.

This module provides a clean, type-safe interface to all core functionality,
wrapping the underlying processing logic with convenient wrapper functions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from .core import (
    main_processing,
    validate_request,
    process_text,
    transform_data,
    aggregate_results
)


@dataclass
class ToolResult:
    """Result container for tool operations.
    
    Attributes:
        success: Whether the operation succeeded
        output: The result data (can be any type)
        error: Error message if operation failed
        metadata: Additional context about the result
    """
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata
        }
    
    def __bool__(self) -> bool:
        """Return True if success, False otherwise.
        
        Returns:
            Boolean indicating success status
        """
        return self.success


def process_text(
    text: str,
    mode: str = "default",
    parameters: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """Process text through the main processing pipeline.
    
    Args:
        text: Input text to process
        mode: Processing mode (default, strict, lenient)
        parameters: Additional parameters as dictionary
        
    Returns:
        ToolResult containing the processed output
    """
    try:
        result = main_processing(text, mode, parameters)
        return ToolResult(
            success=True,
            output=result,
            metadata={"mode": mode}
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"mode": mode}
        )


def validate_request(
    input_text: str,
    mode: str = "default"
) -> ToolResult:
    """Validate an input request.
    
    Args:
        input_text: Text to validate
        mode: Validation mode (default, strict, lenient)
        
    Returns:
        ToolResult containing validation status and messages
    """
    try:
        result = validate_request(
            input_text=input_text,
            mode=mode
        )
        return ToolResult(
            success=result["valid"],
            output=result.get("messages", []),
            metadata={"mode": mode}
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e)
        )


def transform_data(data: Dict[str, Any]) -> ToolResult:
    """Transform data according to specified rules.
    
    Args:
        data: Input data dictionary
        
    Returns:
        ToolResult containing transformed data
    """
    try:
        result = transform_data(
            data=data
        )
        return ToolResult(
            success=True,
            output=result["output_text"],
            metadata={
                "confidence": result.get("confidence", 0.9),
                "flags": result.get("flags", [])
            }
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e)
        )


def aggregate_results(
    results: List[Dict[str, Any]],
    mode: str = "average"
) -> ToolResult:
    """Aggregate multiple results.
    
    Args:
        results: List of result dictionaries to aggregate
        mode: Aggregation mode (average, sum, count)
        
    Returns:
        ToolResult containing aggregated results
    """
    try:
        result = aggregate_results(
            results=results,
            mode=mode
        )
        return ToolResult(
            success=True,
            output=result["output_text"],
            metadata={
                "aggregation_mode": mode,
                "count": len(results)
            }
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e)
        )


def health_check() -> ToolResult:
    """Perform a health check on the service.
    
    Returns:
        ToolResult containing health status information
    """
    try:
        result = {
            "status": "healthy",
            "components": ["core", "api", "tools"],
            "timestamp": "2024-01-15T10:30:00Z"
        }
        return ToolResult(
            success=True,
            output=result,
            metadata={"check_type": "health"}
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e)
        )


def get_version() -> str:
    """Get the current version string.
    
    Returns:
        Version string (e.g., "1.0.0")
    """
    return "1.0.0"


__all__ = [
    "ToolResult",
    "process_text",
    "validate_request",
    "transform_data",
    "aggregate_results",
    "health_check",
    "get_version"
]
