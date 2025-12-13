"""Smoke test: AIQuant adapter feeding rayframe demo factors.

Run manually:
    PYTHONPATH=backend/thirdparty python backend/thirdparty/xquant/factorframework/rayframe/test/aiquant_smoke.py
"""

import os
import sys
from pathlib import Path

# Ensure backend/thirdparty is on sys.path so that `import xquant` works.
thirdparty_root = Path(__file__).resolve().parents[5]
if str(thirdparty_root) not in sys.path:
    sys.path.append(str(thirdparty_root))

os.environ.setdefault("ENV_VERSION", "uat")


def main():
    from xquant.factorframework.rayframe.demo_factors import FactorDemoDay, FactorDemoMin

    demo_cases = [
        ("Day", FactorDemoDay(), "20240101", "20240228", "20240102"),
        ("Min", FactorDemoMin(), "20240101", "20240228", "20240102 09:31:00"),
    ]

    for label, fac, start, end, ts in demo_cases:
        print(f"== {label} factor preload ==")
        inputs = fac.preload_aiquant_inputs(start_date=start, end_date=end)
        for alias, df in inputs.items():
            if isinstance(df, dict):
                for field, sub_df in df.items():
                    print(f"{alias}.{field}", sub_df.head())
            else:
                print(alias, df.head())
        print(f"-- slice at {ts} --")
        sliced = fac.load_inputs(dt_to=ts)
        for alias, df in sliced.items():
            if isinstance(df, dict):
                for field, sub_df in df.items():
                    print(f"{alias}.{field}", sub_df.head())
            else:
                print(alias, df.head())
        print()


if __name__ == "__main__":
    main()
