import os
from pathlib import Path
from typing import Dict, List, Union
from langchain_core.tools import tool

class SafeFileSystem:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def _resolve_safe_path(self, file_path: str) -> Path:
        # Handle potential relative paths or absolute paths
        # If absolute and starts with root, fine.
        # If relative, join with root.
        p = Path(file_path)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self.project_root / p).resolve()
        
        # Security check: ensure path is within project root
        if not str(resolved).startswith(str(self.project_root)):
            raise ValueError(f"Access denied: Path {file_path} is outside project root.")
        return resolved

    def read_file_content(self, file_path: str) -> Dict[str, Union[bool, str]]:
        try:
            path = self._resolve_safe_path(file_path)
            if not path.exists():
                return {"ok": False, "error": "File not found"}
            if not path.is_file():
                return {"ok": False, "error": "Not a file"}
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"ok": True, "content": content}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_directory_contents(self, dir_path: str) -> Dict[str, Union[bool, List[str], str]]:
        try:
            path = self._resolve_safe_path(dir_path)
            if not path.exists():
                return {"ok": False, "error": "Directory not found"}
            if not path.is_dir():
                return {"ok": False, "error": "Not a directory"}
            
            items = os.listdir(path)
            # Filter out hidden files/dirs if needed, but let's keep it simple
            return {"ok": True, "items": sorted(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

# Singleton instance for the tools
# Assuming the project root is the current working directory or passed via env
# For this environment: /Users/fullmetal/Documents/aifactory
PROJECT_ROOT = "/Users/fullmetal/Documents/aifactory"
safe_fs = SafeFileSystem(PROJECT_ROOT)

@tool("read_repo_file")
def read_repo_file(file_path: str) -> Dict:
    """
    Reads the content of a file in the repository.
    Args:
        file_path: Relative path to the file (e.g., 'factors/l3/FactorSecTradeAgg.py')
    """
    return safe_fs.read_file_content(file_path)

@tool("list_repo_dir")
def list_repo_dir(dir_path: str) -> Dict:
    """
    Lists contents of a directory in the repository.
    Args:
        dir_path: Relative path to the directory (e.g., 'factors/l3')
    """
    return safe_fs.list_directory_contents(dir_path)
