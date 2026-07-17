from pathlib import Path
from typing import Dict
from app.core.errors import SecurityViolationError

def normalize_and_validate_zip_entry_path(entry_name: str) -> str:
    r"""
    Normalizes ZIP entry path and rejects dangerous patterns:
    - Absolute paths (starts with / or \)
    - Path traversal (..)
    - NUL byte
    - Windows drive letter prefixes (C:, etc.)
    """
    if "\x00" in entry_name:
        raise SecurityViolationError("ZIP entry path contains NUL byte.")
    
    # Check absolute paths and drive prefixes
    if entry_name.startswith("/") or entry_name.startswith("\\"):
        raise SecurityViolationError(f"Absolute ZIP entry path rejected: {entry_name}")
    
    if len(entry_name) >= 2 and entry_name[1] == ":" and entry_name[0].isalpha():
        raise SecurityViolationError(f"Drive prefix in ZIP entry path rejected: {entry_name}")

    # Normalize path separators
    normalized = entry_name.replace("\\", "/")
    
    # Check traversal
    parts = normalized.split("/")
    if ".." in parts:
        raise SecurityViolationError(f"Path traversal ('..') in ZIP entry path rejected: {entry_name}")
        
    return normalized

def get_blackbox_zdr_headers(zdr_required: bool = True) -> Dict[str, str]:
    """Returns headers for Blackbox requests with ZDR (Zero Data Retention) flag when requested."""
    headers = {
        "Content-Type": "application/json"
    }
    if zdr_required:
        headers["X-Zero-Data-Retention"] = "true"
    return headers
