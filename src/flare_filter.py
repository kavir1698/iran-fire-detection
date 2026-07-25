import json
import logging
from math import radians, sin, cos, sqrt, atan2
from src.config import FLARE_EXCLUSION_PATH

logger = logging.getLogger("flare_filter")


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


class FlareFilter:
    def __init__(self, exclusion_path=FLARE_EXCLUSION_PATH):
        self.exclusion_path = exclusion_path
        self._radius_km = 0.0
        self._flares = []
        self._load_exclusion_zones()

    def _load_exclusion_zones(self):
        try:
            if not self.exclusion_path.exists():
                logger.info(f"Flare exclusion file not found at {self.exclusion_path}. No flare filtering applied.")
                return

            with open(self.exclusion_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._radius_km = float(data.get("exclusion_radius_km", 5.0))
            raw_flares = data.get("flares", [])

            for flare in raw_flares:
                try:
                    name = flare.get("name", "unnamed")
                    lat = float(flare["latitude"])
                    lon = float(flare["longitude"])
                    self._flares.append({"name": name, "latitude": lat, "longitude": lon})
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping malformed flare entry {flare}: {e}")

            logger.info(f"Loaded {len(self._flares)} flare exclusion zone(s) with {self._radius_km:.1f} km radius.")

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse flare exclusion file: {e}. Disabling flare filter.")
            self._flares = []
            self._radius_km = 0.0

    def is_excluded(self, lat, lon):
        if lat is None or lon is None:
            return False
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return False

        if not self._flares or self._radius_km <= 0:
            return False

        for flare in self._flares:
            dist_km = _haversine(lat, lon, flare["latitude"], flare["longitude"])
            if dist_km <= self._radius_km:
                logger.info(
                    f"Hotspot at ({lat:.4f}, {lon:.4f}) excluded — "
                    f"within {dist_km:.1f} km of known flare '{flare['name']}' "
                    f"({flare['latitude']:.4f}, {flare['longitude']:.4f})"
                )
                return True

        return False

    @property
    def active(self):
        return len(self._flares) > 0 and self._radius_km > 0

    @property
    def exclusion_radius_km(self):
        return self._radius_km

    @property
    def flare_count(self):
        return len(self._flares)
