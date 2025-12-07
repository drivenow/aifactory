from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

from domain.codegen.generator import generate_factor_with_semantic_guard
from domain.codegen.view import CodeMode, CodeGenView


def infer_factor_name(code_text: str, fallback: str) -> str:
    """Extract Factor class name inheriting FactorBase; fallback to filename stem."""
    m = re.search(r"class\s+([A-Za-z_][\w]*)\s*\(\s*FactorBase", code_text)
    if m:
        return m.group(1)
    return fallback


def collect_python_files(src_dir: Path) -> List[Path]:
    """Recursively collect Python files under src_dir (excluding __init__.py)."""
    return [
        p
        for p in src_dir.rglob("*.py")
        if p.is_file() and p.name != "__init__.py"
    ]


def convert_file(py_path: Path, out_dir: Path, overwrite: bool) -> Optional[Path]:
    """Convert a single Python factor file to C++ and write to out_dir."""
    code_text = py_path.read_text(encoding="utf-8")
    factor_name = infer_factor_name(code_text, py_path.stem)
    
    out_path = out_dir / f"{factor_name}.cpp"
    if out_path.exists() and not overwrite:
        print(f"[skip] {out_path} already exists (use --overwrite to replace)")
        return None

    state = {
        "factor_name": factor_name,
        "user_spec": "",
        "factor_code": code_text,
        "code_mode": CodeMode.L3_CPP,
        "factor_path": str(out_path),  # Pass target path to view
    }
    
    # Use generator with semantic guard and automatic saving
    view = generate_factor_with_semantic_guard(state, check_agent_round=3)
    
    if view.check_semantics.passed and view.dryrun_result.success:
        return Path(view.factor_path) if view.factor_path else out_path
    else:
        # If generation failed semantic checks, we might still want to inspect the result or log error
        print(f"[warn] Generation for {factor_name} failed checks: {view.check_semantics.reason}")
        return None



def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry: parse args and batch-convert Python factors to C++."""
    parser = argparse.ArgumentParser(
        description="Batch convert Python L3 factor files to C++ via agent"
    )
    parser.add_argument("--src", required=True, help="Source directory containing Python factor files")
    parser.add_argument("--out", required=True, help="Output directory for generated C++ files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    args = parser.parse_args(argv)

    src_dir = Path(args.src).resolve()
    out_dir = Path(args.out).resolve()

    if not src_dir.exists() or not src_dir.is_dir():
        print(f"[error] Source dir not found: {src_dir}")
        return 1

    py_files = collect_python_files(src_dir)
    if not py_files:
        print(f"[info] No python files found under {src_dir}")
        return 0

    print(f"[info] Found {len(py_files)} python files, converting...")
    for p in py_files:
        try:
            out_path = convert_file(p, out_dir, args.overwrite)
            if out_path:
                print(f"[ok] {p.name} -> {out_path}")
        except Exception as e:
            print(f"[error] Failed to convert {p}: {e}")
    return 0


if __name__ == "__main__":
    # 修改为你的实际路径；覆盖输出时取消注释 "--overwrite"
    example_args = [
        "--src", "/path/to/py_factors",
        "--out", "/path/to/output_cpp",
        # "--overwrite",
    ]
    sys.exit(main(example_args))
