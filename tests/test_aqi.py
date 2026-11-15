import pytest

from bdair.aqi import aqi


@pytest.mark.parametrize(
    "conc, expected, category",
    [
        (0.0, 0, "Good"),
        (9.0, 50, "Good"),
        (9.05, 50, "Good"),          # truncated to 9.0, not rounded up
        (9.1, 51, "Moderate"),
        (35.4, 100, "Moderate"),
        (35.5, 101, "Unhealthy for Sensitive Groups"),
        (55.5, 151, "Unhealthy"),
        (125.4, 200, "Unhealthy"),
        (125.5, 201, "Very Unhealthy"),
        (225.5, 301, "Hazardous"),
        (325.4, 500, "Hazardous"),
        (900.0, 500, "Hazardous"),   # beyond the scale is capped
        (-3.0, 0, "Good"),           # negative model output clamps to 0
    ],
)
def test_pm25_breakpoints(conc, expected, category):
    assert aqi("pm2_5", conc) == (expected, category)


def test_pm25_interpolation():
    # (100-51)/(35.4-9.1)*(20.0-9.1)+51 = 71.3 -> 71
    assert aqi("pm2_5", 20.0)[0] == 71


def test_truncation_has_no_float_artefacts():
    # 73.4 * 10 is 733.999... in binary floating point; naive floor() would give 73.3
    assert aqi("pm2_5", 73.4)[0] == 164


def test_pm10_uses_integer_truncation():
    assert aqi("pm10", 54.9) == (50, "Good")
    assert aqi("pm10", 55.0) == (51, "Moderate")
