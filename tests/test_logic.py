import math
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from src.spatial_filter import SpatialFilter, GEOPANDAS_AVAILABLE
from src.weather_client import WeatherClient
from src.social_verifier import SocialVerifier
from src.telegram_notifier import TelegramNotifier
from src.flare_filter import FlareFilter
from pipeline import compute_composite_score, parse_firms_time, parse_confidence, cluster_hotspots

def test_spatial_filter_invalid_coordinates():
    sf = SpatialFilter()
    
    # Test None inputs
    assert sf.is_in_forest_zone(None, 4.0) is False
    assert sf.is_in_forest_zone(36.0, None) is False
    
    # Test string inputs that cannot be parsed
    assert sf.is_in_forest_zone("invalid", 4.0) is False
    assert sf.is_in_forest_zone(36.0, "invalid") is False
    
    # Test NaN inputs
    assert sf.is_in_forest_zone(float('nan'), 4.0) is False
    assert sf.is_in_forest_zone(36.0, float('nan')) is False
    
    # Test points clearly below the 25.0 degree latitude cutoff (outside Iran forest zones)
    assert sf.is_in_forest_zone(24.5, 53.0) is False
    assert sf.is_in_forest_zone(20.0, 50.0) is False

def test_spatial_filter_valid_string_coercion():
    sf = SpatialFilter()
    assert sf.is_in_forest_zone("24.0", "53.0") is False


def test_spatial_filter_inside_forest_zone():
    """Verify that a point inside the forest zone polygon returns True."""
    sf = SpatialFilter()
    if GEOPANDAS_AVAILABLE:
        assert sf.is_in_forest_zone(36.0, 53.0) is True


def test_spatial_filter_outside_forest_zone():
    """Verify that a point outside the polygon but within the fallback bbox returns False."""
    sf = SpatialFilter()
    if GEOPANDAS_AVAILABLE:
        assert sf.is_in_forest_zone(38.0, 51.0) is False


def test_spatial_filter_extreme_south():
    """Verify that a point far south (below 25N hard gate) returns False."""
    sf = SpatialFilter()
    assert sf.is_in_forest_zone(24.0, 55.0) is False


def test_spatial_filter_far_west():
    """Verify that a point west of the polygon (Iraq) returns False."""
    sf = SpatialFilter()
    assert sf.is_in_forest_zone(33.0, 43.0) is False


def test_spatial_filter_tehran():
    """Verify that Tehran (~35.689, 51.389) is inside the forest zone."""
    sf = SpatialFilter()
    if GEOPANDAS_AVAILABLE:
        assert sf.is_in_forest_zone(35.689, 51.389) is True

def test_fire_risk_calculations():
    wc = WeatherClient()
    
    # Test fallback values on missing/None metrics
    assert wc.calculate_fire_risk(None, 15.0, 10.0, 180.0) == 50.0
    assert wc.calculate_fire_risk(40.0, None, 10.0, 180.0) == 50.0
    
    risk = wc.calculate_fire_risk(25.0, 50.0, 15.0, 90.0)
    assert 20.0 <= risk <= 50.0

def test_extreme_wind_multiplier_boost():
    wc = WeatherClient()
    # With extreme wind (temp > 38, humidity < 25, wind_speed > 20)
    risk_extreme = wc.calculate_fire_risk(40.0, 15.0, 25.0, 180.0)
    # Same conditions but without extreme wind multiplier (wind_speed <= 20)
    risk_no_wind = wc.calculate_fire_risk(40.0, 15.0, 15.0, 180.0)

    assert risk_extreme > risk_no_wind

def test_social_verifier_keyword_matching():
    sv = SocialVerifier()
    assert sv.is_fire_related_text("آتش‌سوزی در جنگل‌های مازندران گزارش شد") is True
    assert sv.is_fire_related_text("A wildfire has been reported near Gilan province") is True
    assert sv.is_fire_related_text("Rain and cloudy skies expected tomorrow") is False

def test_social_verifier_spatial_temporal_matching():
    sv = SocialVerifier()
    now = datetime.now(timezone.utc)
    
    hotspot_lat, hotspot_lon = 36.712, 51.420
    hotspot_time = now
    
    reports = [
        # Match within 2km and 1 hour
        {"id": 1, "latitude": 36.715, "longitude": 51.423, "reporter_type": "Citizen", "created_at": now - timedelta(minutes=30)},
        # Too far (> 20km)
        {"id": 2, "latitude": 37.000, "longitude": 52.500, "reporter_type": "Citizen", "created_at": now},
        # Too old (> 5 hours)
        {"id": 3, "latitude": 36.712, "longitude": 51.420, "reporter_type": "Forest Ranger", "created_at": now - timedelta(hours=6)},
    ]
    
    matches = sv.match_reports_with_hotspot(hotspot_lat, hotspot_lon, hotspot_time, reports, max_dist_km=10.0, max_hours=3.0)
    assert len(matches) == 1
    assert matches[0]["report_id"] == 1

def test_social_verifier_score_bonus():
    sv = SocialVerifier()
    assert sv.calculate_score_bonus([]) == 0.0
    assert sv.calculate_score_bonus([{"reporter_type": "Citizen"}]) == 10.0
    assert sv.calculate_score_bonus([{"reporter_type": "Forest Ranger"}]) == 15.0
    assert sv.calculate_score_bonus([{"reporter_type": "Citizen"}, {"reporter_type": "Citizen"}]) == 15.0

def test_composite_score_computation():
    # FRP=50 MW (25 pts), VIIRS=90% (13.5 pts), Cluster=Yes (9 pts), Risk=80 (12 pts), Smoke=Yes (15 pts), Night=Yes (+5 pts), Multi-Sat=2 (+10 pts), Social=+10 pts
    score = compute_composite_score(
        frp=50.0, viirs_confidence=90, cluster_id=0, cluster_size=2,
        risk_score=80.0, smoke_detected=True, smoke_confidence=1.0,
        is_nighttime=True, multi_sensor_count=2, social_bonus=10.0
    )
    assert score == 99.5 or score == 100.0

def test_firms_time_and_confidence_parsing():
    parsed_time = parse_firms_time("2026-07-21", "1430")
    assert parsed_time.hour == 14 and parsed_time.minute == 30
    
    assert parse_confidence("95") == 95
    assert parse_confidence("h") == 95
    assert parse_confidence("l") == 30
    assert parse_confidence("n") == 70

def test_telegram_notifier_cardinals():
    tn = TelegramNotifier()
    assert tn.get_wind_direction_cardinal(0) == "N"
    assert tn.get_wind_direction_cardinal(180) == "S"
    assert tn.get_wind_direction_cardinal(90) == "E"
    assert tn.get_wind_direction_cardinal(270) == "W"

def test_dbscan_clustering():
    hotspots = [
        {"latitude": 36.712, "longitude": 51.420, "acq_date": "2026-07-21", "acq_time": "1200"},
        {"latitude": 36.715, "longitude": 51.423, "acq_date": "2026-07-21", "acq_time": "1205"}, # Close
        {"latitude": 37.500, "longitude": 56.000, "acq_date": "2026-07-21", "acq_time": "1200"}, # Far
    ]
    clusters = cluster_hotspots(hotspots)
    assert clusters[0][0] == clusters[1][0]  # Same cluster
    assert clusters[2][0] == -1  # Noise


class TestFlareFilter:
    @pytest.fixture
    def sample_exclusion_file(self):
        data = {
            "exclusion_radius_km": 5.0,
            "flares": [
                {"name": "South Pars Gas Field", "latitude": 27.5, "longitude": 52.0},
                {"name": "Abadan Refinery", "latitude": 30.35, "longitude": 48.28},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            path = f.name
        yield Path(path)
        Path(path).unlink(missing_ok=True)

    def test_flare_filter_loads_and_excludes(self, sample_exclusion_file):
        ff = FlareFilter(exclusion_path=sample_exclusion_file)
        assert ff.active
        assert ff.exclusion_radius_km == 5.0
        assert ff.flare_count == 2

        assert ff.is_excluded(27.51, 52.01) is True
        assert ff.is_excluded(27.46, 52.02) is True

        assert ff.is_excluded(27.5, 52.1) is False
        assert ff.is_excluded(35.0, 51.0) is False

    def test_flare_filter_invalid_inputs(self, sample_exclusion_file):
        ff = FlareFilter(exclusion_path=sample_exclusion_file)
        assert ff.is_excluded(None, 52.0) is False
        assert ff.is_excluded(27.5, None) is False
        assert ff.is_excluded("invalid", 52.0) is False

    def test_flare_filter_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"exclusion_radius_km": 5.0, "flares": []}, f)
            path = f.name
        try:
            ff = FlareFilter(exclusion_path=Path(path))
            assert not ff.active
            assert ff.flare_count == 0
            assert ff.is_excluded(27.5, 52.0) is False
        finally:
            Path(path).unlink(missing_ok=True)

    def test_flare_filter_missing_file(self):
        ff = FlareFilter(exclusion_path=Path("/nonexistent/flare_zones.json"))
        assert not ff.active
        assert ff.is_excluded(27.5, 52.0) is False

    def test_flare_filter_malformed_entry_skipped(self):
        data = {"exclusion_radius_km": 3.0, "flares": [
            {"name": "Good", "latitude": 31.0, "longitude": 49.0},
            {"name": "Bad", "longitude": 48.0},
            {"name": "Also Good", "latitude": 35.0, "longitude": 44.0},
        ]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            path = f.name
        try:
            ff = FlareFilter(exclusion_path=Path(path))
            assert ff.active
            assert ff.flare_count == 2
            assert ff.is_excluded(31.01, 49.01) is True
            assert ff.is_excluded(31.0, 49.1) is False
        finally:
            Path(path).unlink(missing_ok=True)

