"""Solar-geometry and facade-irradiance physics used to test Vastu's directional claims.

Models (all closed-form, no fitted/learned parameters beyond published constants):

* Solar position - NOAA Global Monitoring Laboratory "General Solar Position
  Calculations" (Fourier series for declination and equation of time).
* Relative optical air mass - Kasten & Young (1989), *Applied Optics* 28, 4735.
* Clear-sky direct normal irradiance - Meinel & Meinel (1976),
  ``I_DN = 1353 * 0.7 ** (AM ** 0.678)`` W/m^2.
* Diffuse sky and ground-reflected components - isotropic (Liu-Jordan) model with
  diffuse horizontal taken as 10 % of beam, ground albedo 0.2 by default.
* Sol-air temperature - ASHRAE Fundamentals:
  ``T_sa = T_o + alpha * I / h_o`` (long-wave term zero for vertical surfaces).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

SOLAR_CONSTANT_MEINEL = 1353.0  # W/m^2, constant used in the Meinel fit


@dataclass(frozen=True)
class Site:
    """Geographic site. Longitude positive east; timezone in hours from UTC."""

    latitude: float
    longitude: float
    timezone: float = 5.5


@dataclass(frozen=True)
class Climate:
    """Design-day air-temperature model and surface constants for sol-air temperature."""

    t_max: float = 39.0  # deg C, daily maximum air temperature
    t_min: float = 28.0  # deg C, daily minimum air temperature
    hour_of_max: float = 15.0  # local solar hour of peak air temperature
    absorptance: float = 0.6  # solar absorptance of the wall finish
    h_out: float = 17.0  # W/(m^2 K), exterior surface film coefficient (ASHRAE summer)
    albedo: float = 0.2  # ground reflectance

    def air_temperature(self, solar_hour: float) -> float:
        mean = 0.5 * (self.t_max + self.t_min)
        amp = 0.5 * (self.t_max - self.t_min)
        return mean + amp * math.cos(2.0 * math.pi * (solar_hour - self.hour_of_max) / 24.0)


@dataclass(frozen=True)
class SunPosition:
    altitude: float  # degrees above horizon
    azimuth: float  # degrees clockwise from true north
    declination: float  # degrees
    hour_angle: float  # degrees, negative before solar noon
    equation_of_time: float  # minutes


def fractional_year(day_of_year: int, hour_utc: float, days_in_year: int = 365) -> float:
    """NOAA fractional year gamma (radians)."""
    return 2.0 * math.pi / days_in_year * (day_of_year - 1 + (hour_utc - 12.0) / 24.0)


def declination_and_eot(gamma: float) -> tuple[float, float]:
    """Solar declination (radians) and equation of time (minutes) from NOAA series."""
    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    return decl, eot


def sun_position(site: Site, day_of_year: int, local_hour: float) -> SunPosition:
    """Topocentric solar altitude/azimuth (no refraction correction)."""
    gamma = fractional_year(day_of_year, local_hour - site.timezone)
    decl, eot = declination_and_eot(gamma)
    time_offset = eot + 4.0 * site.longitude - 60.0 * site.timezone  # minutes
    tst = local_hour * 60.0 + time_offset  # true solar time, minutes
    ha = tst / 4.0 - 180.0  # degrees
    lat = math.radians(site.latitude)
    h = math.radians(ha)
    cos_zen = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(h)
    cos_zen = max(-1.0, min(1.0, cos_zen))
    altitude = 90.0 - math.degrees(math.acos(cos_zen))
    az = math.degrees(
        math.atan2(math.sin(h), math.cos(h) * math.sin(lat) - math.tan(decl) * math.cos(lat))
    )
    azimuth = (az + 180.0) % 360.0
    return SunPosition(altitude, azimuth, math.degrees(decl), ha, eot)


def solar_noon_hour(site: Site, day_of_year: int) -> float:
    """Local clock time (hours) of solar noon, NOAA: snoon = 720 - 4*lon - eqtime (UTC min)."""
    gamma = fractional_year(day_of_year, 12.0 - site.timezone)
    _, eot = declination_and_eot(gamma)
    return (720.0 - 4.0 * site.longitude - eot) / 60.0 + site.timezone


def air_mass(altitude_deg: float) -> float:
    """Kasten-Young (1989) relative optical air mass; ``inf`` below the horizon."""
    if altitude_deg <= 0.0:
        return math.inf
    zen = 90.0 - altitude_deg
    return 1.0 / (math.cos(math.radians(zen)) + 0.50572 * math.pow(96.07995 - zen, -1.6364))


def direct_normal_irradiance(altitude_deg: float) -> float:
    """Meinel clear-sky direct normal irradiance (W/m^2) at sea level."""
    am = air_mass(altitude_deg)
    if math.isinf(am):
        return 0.0
    return SOLAR_CONSTANT_MEINEL * math.pow(0.7, math.pow(am, 0.678))


def vertical_irradiance(
    sun: SunPosition, wall_azimuth: float, albedo: float = 0.2
) -> tuple[float, float]:
    """Total and beam-only irradiance (W/m^2) on a vertical wall whose outward normal
    points to ``wall_azimuth`` (degrees clockwise from true north).

    Beam:   I_b = I_DN * max(0, cos(alt) * cos(A_sun - A_wall))
    Sky:    I_d = 0.5 * I_dh,  with I_dh = 0.1 * I_DN
    Ground: I_r = 0.5 * albedo * (I_DN * sin(alt) + I_dh)
    """
    if sun.altitude <= 0.0:
        return 0.0, 0.0
    dni = direct_normal_irradiance(sun.altitude)
    alt = math.radians(sun.altitude)
    cos_inc = math.cos(alt) * math.cos(math.radians(sun.azimuth - wall_azimuth))
    beam = dni * max(0.0, cos_inc)
    dhi = 0.1 * dni
    ghi = dni * math.sin(alt) + dhi
    total = beam + 0.5 * dhi + 0.5 * albedo * ghi
    return total, beam


@dataclass
class FacadeDay:
    """Integrated daily quantities for one wall orientation on one design day."""

    azimuth: float
    irradiation_kwh: float  # total daily irradiation, kWh/m^2
    morning_kwh: float  # before solar noon
    afternoon_kwh: float  # after solar noon
    peak_sol_air: float  # deg C, daily maximum of the sol-air temperature
    peak_hour: float  # local clock hour at which the sol-air maximum occurs
    mean_sol_air: float  # deg C, 24 h mean (drives the daily conductive heat gain)
    hourly_sol_air: list[float] = field(default_factory=list)

    @property
    def afternoon_fraction(self) -> float:
        return self.afternoon_kwh / self.irradiation_kwh if self.irradiation_kwh > 0 else 0.0


def facade_day(
    site: Site,
    day_of_year: int,
    wall_azimuth: float,
    climate: Climate | None = None,
    step_minutes: float = 5.0,
) -> FacadeDay:
    """Integrate irradiance and sol-air temperature over 24 h by the midpoint rule."""
    climate = climate or Climate()
    noon = solar_noon_hour(site, day_of_year)
    dt_h = step_minutes / 60.0
    n = round(24.0 / dt_h)
    per_hour = max(1, round(1.0 / dt_h))
    total = morning = afternoon = 0.0
    peak, peak_t, sa_sum = -math.inf, 0.0, 0.0
    hourly: list[float] = []
    for k in range(n):
        t = (k + 0.5) * dt_h  # local clock hour
        sun = sun_position(site, day_of_year, t)
        irr, _ = vertical_irradiance(sun, wall_azimuth, climate.albedo)
        e = irr * dt_h / 1000.0  # kWh/m^2
        total += e
        if t < noon:
            morning += e
        else:
            afternoon += e
        solar_hour = t - noon + 12.0
        t_sa = climate.air_temperature(solar_hour) + climate.absorptance * irr / climate.h_out
        if t_sa > peak:
            peak, peak_t = t_sa, t
        sa_sum += t_sa * dt_h
        if k % per_hour == 0:  # one sample per clock hour
            hourly.append(t_sa)
    return FacadeDay(wall_azimuth, total, morning, afternoon, peak, peak_t, sa_sum / 24.0, hourly)


#: Outward normals of the eight principal wall orientations (deg from true north).
EIGHT_AZIMUTHS: tuple[float, ...] = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)

#: Representative design days (day-of-year) for the northern hemisphere.
DESIGN_DAYS: dict[str, int] = {"summer_solstice": 172, "equinox": 80, "winter_solstice": 355}


def facade_table(
    site: Site,
    day_of_year: int,
    climate: Climate | None = None,
    azimuths: tuple[float, ...] = EIGHT_AZIMUTHS,
) -> list[FacadeDay]:
    """Daily facade quantities for a set of wall orientations."""
    return [facade_day(site, day_of_year, a, climate) for a in azimuths]


def noon_altitude(site: Site, day_of_year: int) -> float:
    """Solar altitude at solar noon (degrees)."""
    return sun_position(site, day_of_year, solar_noon_hour(site, day_of_year)).altitude


def overhang_depth_ratio(site: Site, day_of_year: int = 80) -> float:
    """Depth/height ratio of a horizontal overhang that fully shades an equator-facing
    window at solar noon on ``day_of_year`` (default: March equinox).

    d / h = 1 / tan(alpha_noon). On days with a higher noon sun the window stays shaded;
    in winter the lower sun passes beneath the overhang (passive-solar admittance).
    """
    alpha = noon_altitude(site, day_of_year)
    return 1.0 / math.tan(math.radians(alpha))
