"""Core business logic and processing engine.

This module contains the main data structures, algorithms, and processing
functions that form the heart of the Flask API service.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import re
import json
from datetime import datetime


class TextProcessor:
    """Core text processing engine.
    
    Handles text validation, transformation, and aggregation operations.
    """
    
    def __init__(self, mode: str = "default"):
        """Initialize the text processor.
        
        Args:
            mode: Processing mode (default, strict, lenient)
        """
        self.mode = mode
        self.config = {
            "default": {"strictness": 0.5, "tolerance": 0.1},
            "strict": {"strictness": 1.0, "tolerance": 0.0},
            "lenient": {"strictness": 0.0, "tolerance": 0.3}
        }
        
        config = self.config.get(mode, self.config["default"])
        self.strictness = config["strictness"]
        self.tolerance = config["tolerance"]
    
    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """Validate input text.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_valid, list of validation messages)
        """
        messages = []
        
        # Check for empty text
        if not text or not text.strip():
            messages.append("Input text is empty")
            return False, messages
        
        # Check for special characters based on mode
        special_chars = re.findall(r'[^a-zA-Z0-9\s]', text)
        if special_chars and self.strictness > 0.5:
            messages.append(f"Found {len(special_chars)} special characters")
        
        return len(messages) == 0, messages
    
    def transform(self, text: str, flags: List[str] = None) -> Tuple[str, float, List[str]]:
        """Transform text based on rules.
        
        Args:
            text: Input text to transform
            flags: Optional transformation flags
            
        Returns:
            Tuple of (transformed_text, confidence_score, list of flags)
        """
        if flags is None:
            flags = []
        
        # Apply transformations based on mode
        transformed = text
        
        # Capitalization handling
        if "capitalize" in flags:
            transformed = transformed.capitalize()
        
        # Lowercase handling
        if "lowercase" in flags:
            transformed = transformed.lower()
        
        # Remove special characters
        if "sanitize" in flags:
            cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', transformed)
            transformed = cleaned
        
        confidence = 1.0 - (len(flags) * 0.1)
        confidence = max(0.5, min(1.0, confidence))
        
        return transformed, confidence, flags
    
    def aggregate(self, texts: List[str], mode: str = "average") -> Tuple[str, float]:
        """Aggregate multiple text inputs.
        
        Args:
            texts: List of text strings to aggregate
            mode: Aggregation mode (average, sum, count)
            
        Returns:
            Tuple of (aggregated_text, confidence_score)
        """
        if not texts:
            return "", 0.0
        
        if mode == "count":
            return f"Count: {len(texts)}", 1.0
        elif mode == "sum":
            total = sum(len(t) for t in texts)
            return f"Total characters: {total}", 1.0
        else:  # average
            avg_len = sum(len(t) for t in texts) / len(texts)
            return f"Average length: {avg_len:.2f}", 1.0


class DataValidator:
    """Data validation and transformation engine.
    
    Handles JSON data validation, schema checking, and transformation.
    """
    
    def __init__(self):
        """Initialize the data validator."""
        self.schemas = {
            "user": {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }
            },
            "product": {
                "type": "object",
                "required": ["id", "name", "price"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "price": {"type": "number"}
                }
            }
        }
    
    def validate(self, data: Dict[str, Any], schema_name: str) -> Tuple[bool, List[str]]:
        """Validate data against a schema.
        
        Args:
            data: Data to validate
            schema_name: Name of the schema to validate against
            
        Returns:
            Tuple of (is_valid, list of validation messages)
        """
        messages = []
        schema = self.schemas.get(schema_name)
        
        if not schema:
            messages.append(f"Unknown schema: {schema_name}")
            return False, messages
        
        # Check required fields
        for field in schema.get("required", []):
            if field not in data:
                messages.append(f"Missing required field: {field}")
        
        # Validate field types
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    messages.append(f"Field '{field}' should be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    messages.append(f"Field '{field}' should be a number")
        
        return len(messages) == 0, messages
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to rules.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Transformed data dictionary
        """
        # Normalize string fields
        for key in ["name", "email"]:
            if key in data and isinstance(data[key], str):
                data[key] = data[key].strip().lower()
        
        # Validate numeric fields
        for key in ["price"]:
            if key in data and isinstance(data[key], (int, float)):
                data[key] = float(data[key])
        
        return data


class TextAggregator:
    """Text aggregation engine.
    
    Handles combining and analyzing multiple text inputs.
    """
    
    def __init__(self):
        """Initialize the text aggregator."""
        pass
    
    def combine(self, texts: List[str], mode: str = "concatenate") -> str:
        """Combine multiple text inputs.
        
        Args:
            texts: List of text strings to combine
            mode: Combination mode (concatenate, join, merge)
            
        Returns:
            Combined text string
        """
        if not texts:
            return ""
        
        if mode == "join":
            separator = ", "
            return separator.join(texts)
        elif mode == "merge":
            # Simple merge with newlines
            return "\n".join(texts)
        else:  # concatenate
            return "".join(texts)
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text properties.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not text:
            return {
                "length": 0,
                "words": 0,
                "characters": 0
            }
        
        words = text.split()
        characters = len(text)
        
        return {
            "length": characters,
            "words": len(words),
            "characters": characters
        }


# Global instances for use across the application
text_processor = TextProcessor(mode="default")
data_validator = DataValidator()
text_aggregator = TextAggregator()


def main_processing(
    text: str,
    mode: str = "default",
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Main processing function that orchestrates all operations.
    
    Args:
        text: Input text to process
        mode: Processing mode (default, strict, lenient)
        parameters: Additional parameters as dictionary
        
    Returns:
        Dictionary with processing results
    """
    # Initialize processor with specified mode
    processor = TextProcessor(mode=mode)
    
    # Validate input
    is_valid, validation_messages = processor.validate(text)
    
    if not is_valid:
        return {
            "valid": False,
            "messages": validation_messages
        }
    
    # Transform text
    transformed_text, confidence, flags = processor.transform(text, flags=[])
    
    # Aggregate results
    aggregated_text, agg_confidence = processor.aggregate([text], mode="average")
    
    return {
        "valid": True,
        "transformed_text": transformed_text,
        "confidence": confidence,
        "flags": flags,
        "aggregated_text": aggregated_text,
        "aggregation_confidence": agg_confidence
    }


def validate_request(
    input_text: str,
    mode: str = "default"
) -> Dict[str, Any]:
    """Validate an input request.
    
    Args:
        input_text: Text to validate
        mode: Validation mode (default, strict, lenient)
        
    Returns:
        Dictionary with validation status and messages
    """
    processor = TextProcessor(mode=mode)
    is_valid, messages = processor.validate(input_text)
    
    return {
        "valid": is_valid,
        "messages": messages
    }


def transform_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform data according to specified rules.
    
    Args:
        data: Input data dictionary
        
    Returns:
        Dictionary with transformed data
    """
    validator = DataValidator()
    is_valid, messages = validator.validate(data, "user")
    
    if not is_valid:
        return {
            "valid": False,
            "messages": messages
        }
    
    transformed_data = validator.transform(data)
    
    return {
        "output_text": json.dumps(transformed_data),
        "confidence": 0.95,
        "flags": ["normalized", "validated"]
    }


def aggregate_results(
    results: List[Dict[str, Any]],
    mode: str = "average"
) -> Dict[str, Any]:
    """Aggregate multiple results.
    
    Args:
        results: List of result dictionaries to aggregate
        mode: Aggregation mode (average, sum, count)
        
    Returns:
        Dictionary with aggregated results
    """
    aggregator = TextAggregator()
    texts = [r.get("output_text", "") for r in results]
    
    combined_text = aggregator.combine(texts, mode=mode)
    analysis = aggregator.analyze(combined_text)
    
    return {
        "output_text": combined_text,
        "analysis": analysis,
        "aggregation_mode": mode
    }


def health_check() -> Dict[str, Any]:
    """Perform a health check on the service.
    
    Returns:
        Dictionary with health status information
    """
    return {
        "status": "healthy",
        "components": ["core", "api", "tools"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def get_version() -> str:
    """Get the current version string.
    
    Returns:
        Version string (e.g., "1.0.0")
    """
    return "1.0.0"


__all__ = [
    "TextProcessor",
    "DataValidator",
    "TextAggregator",
    "main_processing",
    "validate_request",
    "transform_data",
    "aggregate_results",
    "health_check",
    "get_version"
]
