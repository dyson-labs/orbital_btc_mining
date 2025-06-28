from astropy import units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import get_body_barycentric_posvel
from poliastro.bodies import Earth
from poliastro.twobody.orbit import Orbit
from poliastro.constants import R_earth
import numpy as np
from numpy.linalg import norm

VERBOSE = False  # <--- SET THIS

def twoline2orbit(line1, line2, epoch=None, verbose=VERBOSE):
    from sgp4.api import Satrec
    if epoch is None:
        epoch = Time("2025-03-21T12:00:00")  # Vernal equinox = typical eclipse!
    satellite = Satrec.twoline2rv(line1, line2)
    jd = epoch.jd
    fr = 0.0
    error_code, r, v = satellite.sgp4(jd, fr)
    if error_code != 0:
        raise RuntimeError(f"SGP4 error code: {error_code}")
    r = r * u.km
    v = v * u.km / u.s
    if verbose:
        print(f"[twoline2orbit] r: {r}, v: {v}, epoch: {epoch}")
    return Orbit.from_vectors(Earth, r, v, epoch=epoch)

class OrbitEnvironment:
    def __init__(self, altitude_km=None, inclination_deg=None, duration_hours=24, tle_lines=None, epoch=None, verbose=VERBOSE):
        self.tle_lines = tle_lines
        self.altitude_km = altitude_km
        self.inclination_deg = inclination_deg
        self.duration_hours = duration_hours
        self.verbose = verbose

        if epoch is None:
            self.epoch = Time("2025-03-21T12:00:00")
        else:
            self.epoch = epoch

        self._build_orbit()
        self._run_shadow_pass()
        self._extract_orbital_elements()

    def _build_orbit(self):
        if self.tle_lines:
            self.orbit = twoline2orbit(*self.tle_lines, self.epoch, verbose=self.verbose)
        else:
            self.orbit = Orbit.circular(
                Earth,
                alt=self.altitude_km * u.km,
                inc=self.inclination_deg * u.deg,
                epoch=self.epoch
            )
        if self.verbose:
            print(f"[build_orbit] Orbit constructed: {self.orbit}")

    def _run_shadow_pass(self):
        total_minutes = int(self.duration_hours * 60)
        eclipsed = []
        for i in range(total_minutes):
            t = self.epoch + TimeDelta(i * 60, format='sec')
            try:
                if self.tle_lines:
                    from sgp4.api import Satrec
                    sat = Satrec.twoline2rv(*self.tle_lines)
                    jd = t.jd
                    fr = 0.0
                    error_code, r, v = sat.sgp4(jd, fr)
                    if error_code != 0:
                        raise RuntimeError(f"SGP4 error code: {error_code}")
                    sat_pos = np.array(r)
                else:
                    sat_pos = self.orbit.propagate(t - self.orbit.epoch).r.to_value(u.km)
            except Exception:
                sat_pos = self.orbit.r.to_value(u.km)
            sun_pos = get_body_barycentric_posvel('sun', t)[0].xyz.to_value(u.km)
            earth_pos = get_body_barycentric_posvel('earth', t)[0].xyz.to_value(u.km)
            r_sun = sun_pos - earth_pos

            proj = np.dot(sat_pos, r_sun) / norm(r_sun)
            closest_dist = norm(sat_pos - proj * r_sun / norm(r_sun))
            is_eclipse = (proj > 0) and (closest_dist < R_earth.to_value(u.km))
            if self.verbose and i < 10:
                print(f"t={t.isot}, proj={proj:.2f}, closest_dist={closest_dist:.2f}, is_eclipse={is_eclipse}")
            eclipsed.append(is_eclipse)

        self.eclipse_fraction = np.mean(eclipsed)
        self.sunlight_fraction = 1.0 - self.eclipse_fraction
        self.eclipse_minutes = self.eclipse_fraction * total_minutes

        if self.verbose:
            print(f"[shadow_pass] eclipse_fraction={self.eclipse_fraction:.3f}, sunlight_fraction={self.sunlight_fraction:.3f}")

    def _is_eclipsed(self, r_sat, r_sun):
        proj = np.dot(r_sat, r_sun) / norm(r_sun)
        closest_dist = norm(r_sat - proj * r_sun / norm(r_sun))
        return (proj > 0) and (closest_dist < R_earth.to_value(u.km))

    def _extract_orbital_elements(self):
        if self.tle_lines:
            try:
                r = self.orbit.r  # Astropy Quantity, shape (3,)
                inc = self.orbit.inc
                if self.verbose:
                    print(f"DEBUG: .r = {r} {r.unit} {type(r)} shape: {r.shape}")
                    print(f"DEBUG: .inc = {inc} {inc.unit} {type(inc)}")
                self.altitude_km = np.linalg.norm(r.to(u.km).value) - 6371
                self.inclination_deg = inc.to(u.deg).value
            except Exception as e:
                if self.verbose:
                    print(f"Could not extract orbit elements from TLE: {e}")
                self.altitude_km = None
                self.inclination_deg = None

    def illumination_profile(self, dt=0.1, n_periods=5):
        """Return (time, illumination) arrays for n_periods of this orbit."""
        period_s = 2 * np.pi * np.sqrt(((self.altitude_km+6371)*1e3)**3 / 3.986004418e14)
        n_steps = int(period_s * n_periods / dt)
        illumination = np.zeros(n_steps, dtype=int)
        t0 = self.epoch
        for i in range(n_steps):
            t = t0 + TimeDelta(i*dt, format='sec')
            try:
                sat_pos = self.orbit.propagate(t - self.orbit.epoch).r.to_value(u.km)
            except Exception:
                sat_pos = self.orbit.r.to_value(u.km)
            sun_pos = get_body_barycentric_posvel('sun', t)[0].xyz.to_value(u.km)
            earth_pos = get_body_barycentric_posvel('earth', t)[0].xyz.to_value(u.km)
            r_sun = sun_pos - earth_pos
            illum = not self._is_eclipsed(sat_pos, r_sun)
            illumination[i] = int(illum)
            if self.verbose and i < 10:
                print(f"[illum_prof] t={t.isot}, illum={illum}")
        times = np.arange(n_steps) * dt
        if self.verbose:
            sunlight_frac = np.mean(illumination)
            print(f"[illum_prof] mean sunlight fraction over {n_periods} orbits: {sunlight_frac:.3f}")
        return times, illumination

    def results(self):
        return {
            "altitude_km": self.altitude_km,
            "inclination_deg": self.inclination_deg,
            "sunlight_fraction": self.sunlight_fraction,
            "eclipse_fraction": self.eclipse_fraction,
            "eclipse_minutes": self.eclipse_minutes
        }

if __name__ == "__main__":
    tle_lines = [
        "1 25544U 98067A   24208.58541547  .00005843  00000+0  11057-3 0  9995",
        "2 25544  51.6408  86.1962 0007812 291.5931  68.4848 15.50227972358284"
    ]
    env_tle = OrbitEnvironment(tle_lines=tle_lines, duration_hours=24, verbose=VERBOSE)
    print("\n--- Results (from TLE) ---")
    print(env_tle.results())
    env_circ = OrbitEnvironment(altitude_km=550, inclination_deg=53, duration_hours=24, verbose=VERBOSE)
    print("\n--- Results (circular orbit) ---")
    print(env_circ.results())
