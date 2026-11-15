import itertools
from datetime import date

from bdair.config import CITIES
from bdair.extract import date_chunks, payload_to_frame


def test_date_chunks_cover_range_without_gaps_or_overlap():
    chunks = list(date_chunks(date(2024, 1, 1), date(2024, 12, 31), days=92))
    assert chunks[0][0] == date(2024, 1, 1) and chunks[-1][1] == date(2024, 12, 31)
    for (_, prev_end), (next_start, _) in itertools.pairwise(chunks):
        assert (next_start - prev_end).days == 1


def test_single_day_range():
    assert list(date_chunks(date(2024, 5, 1), date(2024, 5, 1))) == [(date(2024, 5, 1), date(2024, 5, 1))]


def test_payload_to_frame_shapes_and_coerces():
    payload = {"hourly": {"time": ["2024-01-01T00:00", "2024-01-01T01:00"], "pm2_5": [10.5, None]}}
    df = payload_to_frame(payload, CITIES[0], ("pm2_5", "pm10"))
    assert list(df.columns) == ["city_id", "observed_at", "pm2_5", "pm10"]
    assert df["city_id"].unique().tolist() == ["DHK"]
    assert df["pm10"].isna().all()


def test_payload_without_hourly_is_empty():
    assert payload_to_frame({}, CITIES[0], ("pm2_5",)).empty
