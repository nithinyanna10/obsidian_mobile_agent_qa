"""
Pricing Configuration for LLM Models
Prices are per 1 million tokens (as of 2024)
"""
from typing import Optional, Dict

# Pricing per 1M tokens: {"in": input_price, "out": output_price}
PRICE_PER_1M: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 5.00, "out": 15.00},
    "gpt-4-turbo": {"in": 10.00, "out": 30.00},
    "gpt-4": {"in": 30.00, "out": 60.00},
    "gpt-3.5-turbo": {"in": 0.50, "out": 1.50},
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> Optional[float]:
    """
    Calculate cost in USD based on token usage and model pricing.
    
    Args:
        model: Model identifier (e.g., "gpt-4o")
        tokens_in: Number of input tokens
        tokens_out: Number of output tokens
    
    Returns:
        Cost in USD, or None if pricing unknown
    """
    pricing = PRICE_PER_1M.get(model)
    if not pricing:
        return None  # Unknown pricing
    
    cost = (tokens_in / 1_000_000.0) * pricing["in"] + (tokens_out / 1_000_000.0) * pricing["out"]
    return cost


def get_model_from_config() -> str:
    """Get model name from config"""
    from config import OPENAI_MODEL
    return OPENAI_MODEL

