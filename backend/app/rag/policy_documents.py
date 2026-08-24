import json
from typing import Any
from app.database.models.merchant_policy import MerchantPolicy

def normalize_policy_to_text(policy: MerchantPolicy) -> str:
    """
    Normalizes a MerchantPolicy model instance into a clean, semantically rich 
    text representation suitable for embedding and retrieval.
    """
    lines = []
    
    # Add title/identity
    lines.append(f"Policy Name: {policy.policy_name or 'N/A'}")
    lines.append(f"Policy Key: {policy.policy_key or 'N/A'}")
    
    # Add description if available
    if policy.description:
        lines.append(f"Description: {policy.description}")
        
    # Serialize the policy rules/values cleanly
    if policy.policy_value:
        lines.append("Configuration Values and Rules:")
        for key, val in policy.policy_value.items():
            if isinstance(val, dict):
                # Sub-dictionary representation
                sub_lines = []
                for sub_key, sub_val in val.items():
                    sub_lines.append(f"  - {sub_key}: {sub_val}")
                lines.append(f"- {key}:\n" + "\n".join(sub_lines))
            elif isinstance(val, list):
                # List representation
                items = ", ".join(str(item) for item in val)
                lines.append(f"- {key}: [{items}]")
            else:
                lines.append(f"- {key}: {val}")
                
    return "\n".join(lines)
