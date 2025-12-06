"""
Minimal smoke test for evaluate.compute_eval_metrics.
Uses mock_evals by default (no external deps needed).
"""
import pandas as pd

from domain.evaluate.runner import compute_eval_metrics


def test_compute_eval_metrics_mock():
    state = {
        "eval_type": "mock",
        "factor_name": "DemoFactor",
    }
    res = compute_eval_metrics(state)
    assert "ic" in res and "turnover" in res and "group_perf" in res
    assert res["ic"]["ic_mean"] == 0.08
    assert res["turnover"]["turnover"] == 0.3


def test_compute_eval_metrics_l3_fallback_to_mock_when_missing_deps():
    # Provide a tiny dataframe to exercise the code path; without ray/polars it should fallback.
    df = pd.DataFrame(
        {
            "Symbol": ["AAA", "AAA"],
            "MDDate": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
            "f1": [1.0, 2.0],
            "Label_VC_3_2": [0.1, 0.2],
        }
    )
    state = {
        "eval_type": "l3",
        "factor_eval_df": df,
        "factor_list": ["f1"],
        "label_col": "Label_VC_3_2",
        "symbols": ["AAA"],
        "dates": ["2024-01-01", "2024-01-02"],
    }
    res = compute_eval_metrics(state)
    # even if l3 eval fails due to missing deps, we should still return mock structure
    assert "ic" in res and "turnover" in res and "group_perf" in res


if __name__ == "__main__":
    test_compute_eval_metrics_mock()
    test_compute_eval_metrics_l3_fallback_to_mock_when_missing_deps()
    print("evaluate mock tests passed")
