"""
Function Calling Support for Structured Action Output
Provides OpenAI function calling schemas for reliable action parsing
"""
from typing import List, Dict, Any, Optional
import json

def get_action_function_schema() -> Dict[str, Any]:
    """
    Get OpenAI function schema for action generation
    Ensures structured JSON output for reliable parsing
    """
    return {
        "name": "execute_action",
        "description": "Execute a single action on the Android device to progress toward the test goal",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["tap", "type", "swipe", "keyevent", "wait", "assert", "FAIL"],
                    "description": "Type of action to execute"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this action does"
                },
                "x": {
                    "type": "integer",
                    "description": "X coordinate for tap/swipe actions (0-1080 for typical Android screens)"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate for tap/swipe actions (0-1920 for typical Android screens)"
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (for 'type' action) or text to search for (for 'tap' action)"
                },
                "target": {
                    "type": "string",
                    "description": "Target element description for tap actions (e.g., 'Settings button', 'Create vault')"
                },
                "code": {
                    "type": "integer",
                    "description": "Key code for keyevent action (e.g., 4 for BACK, 66 for ENTER)"
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "Swipe direction"
                },
                "distance": {
                    "type": "integer",
                    "description": "Swipe distance in pixels"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for action or failure reason if action is 'FAIL'"
                }
            },
            "required": ["action", "description"]
        }
    }


def parse_function_call_response(response) -> Optional[Dict[str, Any]]:
    """
    Parse OpenAI function calling response into action dictionary
    
    Args:
        response: OpenAI API response object
        
    Returns:
        Action dictionary or None if parsing fails
    """
    try:
        # Check if response has function call
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            
            # Check for function call in message
            if hasattr(choice, 'message'):
                message = choice.message
                
                # Check for function_call (older API format)
                if hasattr(message, 'function_call') and message.function_call:
                    function_call = message.function_call
                    if hasattr(function_call, 'arguments'):
                        args_str = function_call.arguments
                        if isinstance(args_str, str):
                            args = json.loads(args_str)
                        else:
                            args = args_str
                        return args
                
                # Check for tool_calls (newer API format)
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    tool_call = message.tool_calls[0]
                    if hasattr(tool_call, 'function'):
                        function = tool_call.function
                        if hasattr(function, 'arguments'):
                            args_str = function.arguments
                            if isinstance(args_str, str):
                                args = json.loads(args_str)
                            else:
                                args = args_str
                            return args
                
                # Fallback: check message content for JSON
                if hasattr(message, 'content') and message.content:
                    content = message.content
                    # Try to parse as JSON
                    try:
                        if isinstance(content, str):
                            # Try to extract JSON from content
                            if '{' in content:
                                json_start = content.find('{')
                                json_end = content.rfind('}') + 1
                                if json_end > json_start:
                                    json_str = content[json_start:json_end]
                                    return json.loads(json_str)
                    except:
                        pass
        
        return None
    except Exception as e:
        print(f"  ⚠️  Error parsing function call: {e}")
        return None


def format_action_for_function_call(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format action dictionary to match function schema
    
    Args:
        action: Action dictionary
        
    Returns:
        Formatted action dictionary
    """
    formatted = {
        "action": action.get("action", "tap"),
        "description": action.get("description", "")
    }
    
    # Add optional fields if present
    if "x" in action:
        formatted["x"] = action["x"]
    if "y" in action:
        formatted["y"] = action["y"]
    if "text" in action:
        formatted["text"] = action["text"]
    if "target" in action:
        formatted["target"] = action["target"]
    if "code" in action:
        formatted["code"] = action["code"]
    if "direction" in action:
        formatted["direction"] = action["direction"]
    if "distance" in action:
        formatted["distance"] = action["distance"]
    if "reason" in action:
        formatted["reason"] = action["reason"]
    
    return formatted
