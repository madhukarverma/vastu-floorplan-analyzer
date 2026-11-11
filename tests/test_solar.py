import math

import pytest

from vastu_analyzer import solar

DELHI = solar.Site(28.6139, 77.2090, 5.5)
CHENNAI = solar.Site(13.0827, 80.2707, 5.5)


def test_declination_extremes() -> None:
    decl_jun, _ = solar.declination_and_eot(solar.fractional_year(172, 12))
    decl_dec, _ = solar.declination_and_eot(solar.fractional_year(355, 12))
    assert math.degrees(decl_jun) == pytest.approx(23.44, abs=0.1)
    assert math.degrees(decl_dec) == pytest.approx(-23.44, abs=0.1)


def test_equation_of_time_known_values() -> None:
    # Early November: sundial is ~16 min fast; mid-February: ~14 min slow.
    _, eot_nov = solar.declination_and_eot(solar.fractional_year(307, 12))
    _, eot_feb = solar.declination_and_eot(solar.fractional_year(42, 12))
    assert eot_nov == pytest.approx(16.4, abs=0.5)
    assert eot_feb == pytest.approx(-14.2, abs=0.5)


@pytest.mark.parametrize(
    ("doy", "expected"), [(172, 90 - 28.6139 + 23.44), (355, 90 - 28.6139 - 23.44)]
)
def test_noon_altitude_matches_spherical_astronomy(doy: int, expected: float) -> None:
    assert solar.noon_altitude(DELHI, doy) == pytest.approx(expected, abs=0.1)


def test_noon_azimuth_and_morning_sun() -> None:
    noon = solar.solar_noon_hour(DELHI, 172)
    assert 12.2 < noon < 12.5  # Delhi lies west of the 82.5 E IST meridian
    assert solar.sun_position(DELHI, 172, noon).azimuth == pytest.approx(180.0, abs=0.5)
    morning = solar.sun_position(DELHI, 172, 7.0)
    assert 0 < morning.azimuth < 90  # June sunrise is north of east
    assert morning.altitude > 0
    # South of the Tropic of Cancer the June noon sun stands in the north.
    noon_c = solar.solar_noon_hour(CHENNAI, 172)
    az = solar.sun_position(CHENNAI, 172, noon_c).azimuth
    assert min(az, 360 - az) < 1.0


def test_air_mass_and_dni() -> None:
    assert solar.air_mass(90.0) == pytest.approx(1.0, abs=1e-3)
    assert solar.air_mass(30.0) == pytest.approx(2.0, abs=0.01)
    assert math.isinf(solar.air_mass(-1.0))
    assert solar.direct_normal_irradiance(90.0) == pytest.approx(1353 * 0.7, rel=1e-3)
    assert solar.direct_normal_irradiance(-5.0) == 0.0


def test_vertical_irradiance_geometry() -> None:
    sun = solar.SunPosition(altitude=30.0, azimuth=90.0, declination=0, hour_angle=-60,
                            equation_of_time=0)  # fmt: skip
    total_e, beam_e = solar.vertical_irradiance(sun, 90.0)
    _, beam_w = solar.vertical_irradiance(sun, 270.0)
    dni = solar.direct_normal_irradiance(30.0)
    assert beam_e == pytest.approx(dni * math.cos(math.radians(30)))
    assert beam_w == 0.0
    assert total_e > beam_e
    night = solar.SunPosition(-10, 0, 0, 180, 0)
    assert solar.vertical_irradiance(night, 0.0) == (0.0, 0.0)


def test_east_west_symmetry_and_sol_air_asymmetry() -> None:
    east = solar.facade_day(DELHI, 172, 90.0)
    west = solar.facade_day(DELHI, 172, 270.0)
    # Irradiation is symmetric about solar noon ...
    assert east.irradiation_kwh == pytest.approx(west.irradiation_kwh, rel=0.01)
    assert east.morning_kwh > east.afternoon_kwh
    assert west.afternoon_fraction > 0.8
    # ... but the west peak coincides with the air-temperature peak.
    assert west.peak_sol_air > east.peak_sol_air + 3.0
    assert west.peak_hour > 14.0 > east.peak_hour
    assert len(east.hourly_sol_air) == 24


def test_winter_favours_south_wall() -> None:
    table = {f.azimuth: f for f in solar.facade_table(DELHI, 355)}
    assert table[180.0].irradiation_kwh == max(f.irradiation_kwh for f in table.values())
    assert table[0.0].irradiation_kwh < table[180.0].irradiation_kwh / 4


def test_overhang_ratio() -> None:
    alpha = solar.noon_altitude(DELHI, 80)
    assert solar.overhang_depth_ratio(DELHI) == pytest.approx(1 / math.tan(math.radians(alpha)))
