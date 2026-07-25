import math
import logging
from src.config import GEOJSON_PATH

logger = logging.getLogger("spatial_filter")

try:
    import geopandas as gpd
    from shapely.geometry import Point
    from shapely.ops import unary_union
    GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
    Point = None
    unary_union = None
    GEOPANDAS_AVAILABLE = False


class SpatialFilter:
    def __init__(self, geojson_path=GEOJSON_PATH):
        self.geojson_path = geojson_path
        self.boundary = None
        self._fallback = False
        self._load_boundary()

    def _load_boundary(self):
        if not GEOPANDAS_AVAILABLE:
            logger.warning("geopandas/shapely not installed. ALL hotspots will pass through permissive fallback bbox.")
            self._fallback = True
            return

        try:
            if not self.geojson_path.exists():
                raise FileNotFoundError(f"GeoJSON file not found at {self.geojson_path}")

            gdf = gpd.read_file(self.geojson_path)
            logger.info(f"Loaded {len(gdf)} feature(s) from {self.geojson_path}")

            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
            elif not gdf.crs.equals("EPSG:4326"):
                gdf = gdf.to_crs(epsg=4326)

            geometries = []
            for i, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue

                if not geom.is_valid:
                    logger.warning(f"Feature {i} geometry is INVALID. Attempting repair...")
                    try:
                        from shapely.validation import make_valid
                        geom = make_valid(geom)
                    except ImportError:
                        pass
                    geom = geom.buffer(0)

                if geom.is_valid:
                    geometries.append(geom)
                else:
                    logger.warning(f"Feature {i} geometry still INVALID after repair — skipping.")

            if not geometries:
                logger.error("No valid geometries in GeoJSON. Falling back to permissive bbox.")
                self._fallback = True
                return

            self.boundary = unary_union(geometries)
            if not self.boundary.is_valid:
                logger.warning("Merged boundary invalid — applying buffer(0).")
                self.boundary = self.boundary.buffer(0)

            if self.boundary.is_valid:
                logger.info(f"Forest zone boundary ready. Area: {self.boundary.area:.4f} sq deg")
            else:
                logger.error("Boundary geometry could not be made valid. Falling back to permissive bbox.")
                self.boundary = None
                self._fallback = True

        except Exception as e:
            logger.error(f"Failed to load GeoJSON boundary: {e}. ALL hotspots will pass permissive fallback bbox.")
            self._fallback = True

    def is_in_forest_zone(self, lat, lon):
        if lat is None or lon is None:
            return False
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return False
        if math.isnan(lat) or math.isnan(lon):
            return False

        if lat < 25.0:
            return False

        if self._fallback or self.boundary is None:
            logger.warning(f"No spatial boundary loaded — using permissive fallback bbox for ({lat:.4f}, {lon:.4f}).")
            return 25.0 <= lat <= 39.8 and 44.0 <= lon <= 63.3

        try:
            point = Point(lon, lat)
            return self.boundary.covers(point) or self.boundary.contains(point)
        except Exception as e:
            logger.error(f"Spatial lookup failed for ({lat:.4f}, {lon:.4f}): {e}")
            return False
