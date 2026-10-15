import os

from . import formatters
from .config import ServerConfig


def is_valid_dir(dir_path: str):
    if not os.path.isdir(dir_path):
        raise NotADirectoryError(f"{dir_path} is not a valid directory or not exists.")

def path_exists(path:str):
    if not os.path.exists(path):
        raise FileExistsError(f"Path not exists:{path}")

def validate_symlink(link_path):
    real_path = os.path.realpath(link_path)
    normalized_real = formatters.normalize_path(real_path)
    is_real_allowed  = ServerConfig().is_allowed_path(normalized_real)
    if not is_real_allowed:
        raise PermissionError(
            "Access denied - symlink points out of allowed directories"
        )
    return real_path

def __validate_absolute_path(absolute_path):
    normalized_requested = formatters.normalize_path(absolute_path)
    is_allowed = ServerConfig().is_allowed_path(normalized_requested)
    if not is_allowed:
        raise PermissionError(
            f"Access denied - path outside allowed directories: {absolute_path}"
        )

def validate_path(path:str, validate_parent=False):
    expanded_path = formatters.expand_home(path)
    absolute_path = os.path.abspath(expanded_path)
    try:
        path_exists(absolute_path)
    except FileExistsError:
        if not validate_parent:
            raise
        # If the file does not exist yet, we validate its parent directory
        __validate_absolute_path(os.path.dirname(absolute_path))
        return absolute_path

    if os.path.islink(absolute_path):
        return validate_symlink(path)

    __validate_absolute_path(absolute_path)
    
    return absolute_path
    

