from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from domain.codegen.generator import generate_factor_code_from_spec
from domain.codegen.view import CodeMode


def load_specs(json_path: Path) -> List[Dict[str, Any]]:
    """Load spec list from JSON file (list or {'items': [...]})"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # allow {"items": [...]} wrapper
        items = data.get("items")
        if isinstance(items, list):
            return items
        raise ValueError("JSON must be a list or contain 'items' list")
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of specs")
    return data


def ensure_str(val: Any, default: str = "") -> str:
    """Coerce value to string with default fallback."""
    return str(val) if val is not None else default


def convert_spec(spec: Dict[str, Any], out_dir: Path, overwrite: bool) -> Optional[Path]:
    """Convert one spec dict to Python factor code and write to out_dir."""
    factor_name = ensure_str(spec.get("factor_name") or spec.get("name"), "").strip()
    if not factor_name:
        raise ValueError("factor_name is required in spec")
    user_spec = ensure_str(spec.get("user_spec") or spec.get("desc") or spec.get("description"), "")
    factor_code = ensure_str(spec.get("factor_code") or spec.get("code"), "")

    state = {
        "factor_name": factor_name,
        "user_spec": user_spec,
        "factor_code": factor_code,
        "code_mode": CodeMode.L3_PY,
    }
    py_code = generate_factor_code_from_spec(state)

    out_path = out_dir / f"{factor_name}.py"
    if out_path.exists() and not overwrite:
        print(f"[skip] {out_path} already exists (use --overwrite to replace)")
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(py_code, encoding="utf-8")
    return out_path


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry: parse args and batch-generate Python factors from JSON specs."""
    parser = argparse.ArgumentParser(
        description="Batch generate Python L3 factors from JSON specs"
    )
    parser.add_argument("--json", required=True, help="Path to JSON file containing factor specs")
    parser.add_argument("--out", required=True, help="Output directory for generated Python files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    args = parser.parse_args(argv)

    json_path = Path(args.json).resolve()
    out_dir = Path(args.out).resolve()

    if not json_path.exists():
        print(f"[error] JSON file not found: {json_path}")
        return 1

    try:
        specs = load_specs(json_path)
    except Exception as e:
        print(f"[error] Failed to parse JSON: {e}")
        return 1

    if not specs:
        print("[info] No specs found in JSON")
        return 0

    print(f"[info] Loaded {len(specs)} specs, generating Python factors...")
    for spec in specs:
        try:
            out_path = convert_spec(spec, out_dir, args.overwrite)
            if out_path:
                print(f"[ok] {spec.get('factor_name') or spec.get('name')} -> {out_path}")
        except Exception as e:
            print(f"[error] Failed to generate factor for spec {spec}: {e}")
    return 0


if __name__ == "__main__":
    # 修改为你的实际 JSON 路径与输出目录；覆盖输出时取消注释 "--overwrite"
    example_args = [
        "--json", "/path/to/factors.json",
        "--out", "/path/to/output_py",
        # "--overwrite",
    ]
    sys.exit(main(example_args))
