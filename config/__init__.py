""" 
prompt imports 
"""

import os
import yaml
from pathlib import Path
from string import Formatter

# Get the directory where the __init__.py file is located
_config_dir = Path(os.path.dirname(os.path.abspath(__file__)))
_system_prompt_path = _config_dir / "system_prompts.yaml"
_user_prompts_path = _config_dir / "user_prompts.yaml"
_model_path = _config_dir / "models.yaml"

# Load the prompts from YAML
with open(_system_prompt_path, "r") as f:
    system_prompts = yaml.safe_load(f)

# Load the prompts from YAML
with open(_model_path, "r") as f:
    models = yaml.safe_load(f)
    
# Load the prompt templates from YAML
with open(_user_prompts_path, "r") as f:
    user_prompts = yaml.safe_load(f)


def format_user_prompt(user_prompt_name, **kwargs):
    """
    Format a user prompt template with the given parameters.
    
    Args:
        user_prompt_name: Name of the template in the YAML file
        **kwargs: Parameters to fill into the template
        
    Returns:
        Formatted user prompt string
    
    Raises:
        KeyError: If user pormpt name doesn't exist
        ValueError: If required parameters are missing
    """
    if user_prompt_name not in user_prompts:
        raise KeyError(f"User Prompt:  '{user_prompt_name}' not found in user_prompts.yaml")
    
    user_prompt = user_prompts[user_prompt_name]
    
    # Check for missing parameters
    required_params = {param for _, param, _, _ in Formatter().parse(user_prompt) if param}
    missing_params = required_params - set(kwargs.keys())
    
    if missing_params:
        raise ValueError(f"Missing required parameters for template '{user_prompt_name}': {missing_params}")
    
    # Format the template
    return user_prompt.format(**kwargs)
