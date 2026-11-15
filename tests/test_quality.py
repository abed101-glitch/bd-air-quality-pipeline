import pandas as pd

from bdair.quality import completeness, drop_unavailable, validate

COLS = ["pm2_5", "pm10"]


def frame(rows):
    df = pd.DataFrame(rows, columns=["city_id", "observed_at", *COLS])
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    return df


def test_clean_rows_pass_through():
    df = frame([("DHK", "2025-01-01 00:00", 80.0, 120.0), ("DHK", "2025-01-01 01:00", 75.0, 110.0)])
    clean, bad = validate(df, COLS)
    assert len(clean) == 2 and bad.empty


def test_negative_and_out_of_range_are_quarantined_with_reason():
    df = frame([
        ("DHK", "2025-01-01 00:00", -1.0, 120.0),
        ("DHK", "2025-01-01 01:00", 5000.0, 110.0),
        ("DHK", "2025-01-01 02:00", 50.0, 90.0),
    ])
    clean, bad = validate(df, COLS)
    assert len(clean) == 1
    assert set(bad["reason"]) == {"negative_pm2_5", "out_of_range_pm2_5"}


def test_duplicates_keep_first_and_quarantine_rest():
    df = frame([("DHK", "2025-01-01 00:00", 50.0, 90.0), ("DHK", "2025-01-01 00:00", 51.0, 91.0)])
    clean, bad = validate(df, COLS)
    assert clean["pm2_5"].tolist() == [50.0]
    assert bad["reason"].tolist() == ["duplicate_key"]


def test_multiple_reasons_are_joined():
    df = frame([("DHK", "2025-01-01 00:00", -1.0, -2.0)])
    _, bad = validate(df, COLS)
    assert bad["reason"].iloc[0] == "negative_pm2_5;negative_pm10"


def test_missing_key_is_quarantined():
    df = frame([(None, "2025-01-01 00:00", 50.0, 90.0)])
    clean, bad = validate(df, COLS)
    assert clean.empty and bad["reason"].iloc[0] == "missing_key"


def test_unpublished_hours_are_dropped_not_quarantined():
    df = frame([("DHK", "2025-01-01 00:00", None, None), ("DHK", "2025-01-01 01:00", 50.0, None)])
    kept, dropped = drop_unavailable(df, COLS)
    assert dropped == 1 and len(kept) == 1


def test_completeness():
    df = frame([("DHK", f"2025-01-01 {h:02d}:00", 1.0, 1.0) for h in range(18)])
    assert completeness(df, 24)["completeness"].iloc[0] == 0.75


def test_empty_frame():
    clean, bad = validate(frame([]), COLS)
    assert clean.empty and bad.empty
