"""
Iran Fire Watch — Streamlit Dashboard
Real-time satellite active-fire detection & AI verification platform.
"""

import base64
import json
import logging
import re
import time
import uuid
from datetime import datetime, time as dt_time, timezone, timedelta
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.config import GEOJSON_PATH
from src.db_client import DbClient
from src.spatial_filter import SpatialFilter

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Iran Fire Watch — سامانه پایش آتش‌سوزی",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════
# TRANSLATIONS (pure text — no HTML)
# ═══════════════════════════════════════════════════════════════
T = {
    "en": {
        "sidebar_title": "Iran Fire Watch",
        "connected": "Connected to database.",
        "demo_mode": "Demo mode — simulated data.",
        "data_sources": "NASA FIRMS (VIIRS 3-satellite)  ·  Copernicus Sentinel-2  ·  Open-Meteo Weather API",
        "pipeline_info": "Pipeline v2: Multi-sensor fusion  ·  DBSCAN clustering  ·  Composite scoring (0–100)",
        "visit_stats": "Visitor Analytics",
        "active_visitors": "Active Visitors",
        "total_visitors": "Total Visitors",
        "main_title": "Iran Forest Fire Detection Platform",
        "subtitle": "Real‑time satellite active‑fire trigger & AI‑verified early‑warning system",
        "stat_confirmed": "Active Fires",
        "stat_pending": "Awaiting Verification",
        "stat_false": "False Alarms",
        "stat_resolved": "Resolved",
        "stat_sirocco": "Extreme Wind Risk",
        "filter_status": "Status",
        "filter_province": "Province",
        "filter_frp": "Min FRP (MW)",
        "filter_all": "All",
        "warnings_title": "Warnings & Log",
        "no_data": "No fires match the selected filters.",
        "fire_confirmed": "Confirmed Fire",
        "thermal_pending": "Pending Verification",
        "false_alarm": "False Positive",
        "resolved_fire": "Resolved",
        "province": "Province",
        "coordinates": "Coordinates",
        "detection": "Detected",
        "risk_score": "Risk Score",
        "frp": "FRP",
        "confidence": "Confidence",
        "time": "Time",
        "temp": "Temperature",
        "humidity": "Humidity",
        "wind": "Wind",
        "risk": "Fire Risk",
        "sentinel_quicklook": "Sentinel-2 Quicklook",
        "footer": "Iran Forest Fire detection & early-warning platform. Data: NASA FIRMS (VIIRS/MODIS) | Copernicus Sentinel-2 | Open‑Meteo.",
        "verification_title": "Ground Verification & Citizen Fire Report",
        "verification_subtitle": "Report an active fire or confirm a satellite detection. Photo proof is mandatory.",
        "submit_report": "Submit Report",
        "reporter_label": "Reporter Category",
        "reporter_name": "Reporter Name (optional)",
        "severity_label": "Fire Severity",
        "loc_method": "Location Input Method",
        "gps_auto": "GPS Auto‑Detect",
        "manual_coords": "Province & Manual Coordinates",
        "photos_required": "Photo Proof (mandatory)",
        "upload_photo": "Upload Photo",
        "take_snapshot": "Take Camera Snapshot",
        "desc_label": "Description & Notes",
        "report_success": "Report submitted successfully. Report ID: {id}. Thank you for protecting Iran's forests.",
        "report_err_photo": "You must upload a photo or take a camera snapshot to submit a report.",
        "report_err_general": "Failed to record report: {err}",
        "citizen": "Local Citizen",
        "ranger": "Forest Ranger",
        "fire_dept": "Fire Department",
        "severity_smoke": "Active Smoke Plume",
        "severity_flames": "Visible Flames Spreading",
        "severity_ext": "Extinguished",
        "date_range": "Date Range",
    },
    "fa": {
        "sidebar_title": "پایش آتش‌سوزی ایران",
        "connected": "متصل به پایگاه داده.",
        "demo_mode": "حالت نمایشی — داده‌های شبیه‌سازی شده.",
        "data_sources": "NASA FIRMS (سه ماهواره VIIRS)  ·  Copernicus Sentinel-2  ·  Open-Meteo هواشناسی",
        "pipeline_info": "خط پردازش v2: ادغام چندحسگری  ·  خوشه‌بندی DBSCAN  ·  امتیازدهی ترکیبی (۰–۱۰۰)",
        "visit_stats": "آمار بازدید",
        "active_visitors": "بازدیدکنندگان فعال",
        "total_visitors": "کل بازدیدکنندگان",
        "main_title": "سامانه پایش آتش‌سوزی جنگل‌های ایران",
        "subtitle": "سامانه هشدار زودهنگام مبتنی بر ماهواره و هوش مصنوعی",
        "stat_confirmed": "آتش‌سوزی‌های فعال",
        "stat_pending": "در انتظار تأیید",
        "stat_false": "هشدارهای کذب",
        "stat_resolved": "خاموش شده",
        "stat_sirocco": "خطر باد شدید",
        "filter_status": "وضعیت",
        "filter_province": "استان",
        "filter_frp": "حداقل FRP (MW)",
        "filter_all": "همه",
        "warnings_title": "هشدارها و گزارش",
        "no_data": "آتش‌سوزی فعالی برای معیارهای انتخاب شده یافت نشد.",
        "fire_confirmed": "آتش‌سوزی تأیید شده",
        "thermal_pending": "در انتظار تأیید",
        "false_alarm": "هشدار کذب",
        "resolved_fire": "خاموش شده",
        "province": "استان",
        "coordinates": "مختصات",
        "detection": "زمان تشخیص",
        "risk_score": "امتیاز خطر",
        "frp": "FRP",
        "confidence": "اطمینان",
        "time": "زمان",
        "temp": "دما",
        "humidity": "رطوبت",
        "wind": "باد",
        "risk": "خطر",
        "sentinel_quicklook": "تصویر Sentinel-2",
        "footer": "سامانه پایش و هشدار زودهنگام آتش‌سوزی جنگل‌های ایران. منابع داده: NASA FIRMS | Copernicus Sentinel-2 | Open‑Meteo.",
        "verification_title": "گزارش میدانی و تأیید آتش‌سوزی",
        "verification_subtitle": "گزارش آتش‌سوزی فعال یا تأیید تشخیص ماهواره‌ای. تصویر الزامی است.",
        "submit_report": "ارسال گزارش",
        "reporter_label": "نوع گزارش‌دهنده",
        "reporter_name": "نام گزارش‌دهنده (اختیاری)",
        "severity_label": "شدت آتش‌سوزی",
        "loc_method": "روش تعیین موقعیت",
        "gps_auto": "تشخیص خودکار GPS",
        "manual_coords": "انتخاب استان و مختصات",
        "photos_required": "تصویر (الزامی)",
        "upload_photo": "بارگذاری تصویر",
        "take_snapshot": "عکس با دوربین",
        "desc_label": "توضیحات",
        "report_success": "گزارش با موفقیت ثبت شد. شماره گزارش: {id}. از شما برای حفاظت از جنگل‌های ایران سپاسگزاریم.",
        "report_err_photo": "برای ارسال گزارش باید تصویر بارگذاری یا عکس بگیرید.",
        "report_err_general": "خطا در ثبت گزارش: {err}",
        "citizen": "شهروند",
        "ranger": "محیط‌بان",
        "fire_dept": "آتش‌نشانی",
        "severity_smoke": "دود فعال",
        "severity_flames": "شعله‌های قابل مشاهده",
        "severity_ext": "خاموش شده",
        "date_range": "بازه زمانی",
    },
}

# ═══════════════════════════════════════════════════════════════
# CSS — Centralized dark glassmorphism theme
# ═══════════════════════════════════════════════════════════════
CSS = r"""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&family=Noto+Naskh+Arabic:wght@400;500;600&display=swap');

/* ── Base ── */
:root {
    --bg-primary:   #090c10;
    --bg-card:      rgba(15, 20, 28, 0.75);
    --border-card:  rgba(255, 255, 255, 0.06);
    --text-primary: #e2e8f0;
    --text-muted:   #94a3b8;
    --text-dim:     #64748b;
    --red:          #f43f5e;
    --amber:        #f59e0b;
    --emerald:      #10b981;
    --blue:         #3b82f6;
    --cyan:         #06b6d4;
    --slate:        #64748b;
}

.stApp {
    background-color: var(--bg-primary);
    background-image:
        radial-gradient(circle at 10% 20%, rgba(244, 63, 94, 0.04) 0%, transparent 90%),
        radial-gradient(circle at 90% 80%, rgba(245, 158, 11, 0.03) 0%, transparent 90%);
    color: var(--text-primary);
    font-family: 'Outfit', 'Vazirmatn', 'Noto Naskh Arabic', sans-serif;
}

section[data-testid="stSidebar"] {
    background-color: #0c1016 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
}

/* ── Typography ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', 'Vazirmatn', sans-serif !important;
    font-weight: 700 !important;
}

/* ── Cards ── */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 20px 18px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    margin-bottom: 16px;
    height: 100%;
    transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
}
.glass-card:hover {
    transform: translateY(-2px);
    border-color: rgba(244, 63, 94, 0.25);
    box-shadow: 0 12px 40px rgba(244, 63, 94, 0.08);
}

/* ── Stat cards ── */
.stat-card-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.stat-card-value {
    font-size: 34px;
    font-weight: 700;
    line-height: 1.1;
}
.stat-card-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 4px;
}

.text-red    { background: linear-gradient(135deg, #f43f5e 0%, #b91c1c 100%); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.text-amber  { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.text-emerald{ background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.text-slate  { color: var(--slate); }
.text-danger { background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

/* ── Warning cards ── */
.warn-card {
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.warn-card-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 6px;
}
.warn-card-detail {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
}

/* ── Sidebar visitor badge ── */
.sidebar-badge {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 16px;
}
.sidebar-badge-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--emerald);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}
.sidebar-badge-row {
    font-size: 13px;
    color: var(--text-primary);
    margin-bottom: 2px;
}

/* ── RTL ── */
.rtl { direction: rtl; text-align: right; }
.ltr { direction: ltr; text-align: left; }

/* ── Divider ── */
hr.divider { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.06); margin: 20px 0; }

/* ── Footer ── */
.footer { text-align: center; color: var(--text-dim); font-size: 12px; margin-top: 8px; }

/* ── Streamlit overrides ── */
.stAlert {
    background: rgba(220, 38, 38, 0.1) !important;
    border: 1px solid rgba(220, 38, 38, 0.25) !important;
    border-radius: 12px !important;
}
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #f43f5e, #f59e0b) !important;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PROVINCE (OSTAN) LOOKUP
# ═══════════════════════════════════════════════════════════════
PROVINCE_BOUNDS = {
    "Mazandaran / مازندران":                  {"lat": (35.80, 36.95), "lon": (50.50, 54.20)},
    "Gilan / گیلان":                           {"lat": (36.50, 38.00), "lon": (48.50, 50.50)},
    "Golestan / گلستان":                       {"lat": (36.50, 38.10), "lon": (54.00, 56.50)},
    "Ardabil / اردبیل":                        {"lat": (37.20, 39.30), "lon": (47.40, 48.80)},
    "East Azerbaijan / آذربایجان شرقی":        {"lat": (37.00, 39.30), "lon": (45.50, 48.30)},
    "West Azerbaijan / آذربایجان غربی":        {"lat": (36.00, 39.30), "lon": (44.00, 47.00)},
    "Kurdistan / کردستان":                     {"lat": (34.80, 36.50), "lon": (45.50, 48.20)},
    "Kermanshah / کرمانشاه":                   {"lat": (33.50, 35.30), "lon": (45.50, 48.00)},
    "Lorestan / لرستان":                       {"lat": (32.80, 34.50), "lon": (47.00, 50.00)},
    "Ilam / ایلام":                             {"lat": (31.80, 34.00), "lon": (45.50, 48.00)},
    "Chaharmahal & Bakhtiari / چهارمحال و بختیاری": {"lat": (31.50, 32.80), "lon": (49.50, 51.30)},
    "Kohgiluyeh & Boyer-Ahmad / کهگیلویه و بویراحمد": {"lat": (30.30, 31.70), "lon": (50.20, 51.80)},
    "Fars / فارس":                             {"lat": (28.50, 31.50), "lon": (51.00, 55.00)},
    "North Khorasan / خراسان شمالی":           {"lat": (36.50, 38.30), "lon": (56.00, 58.50)},
    "Razavi Khorasan / خراسان رضوی":           {"lat": (34.00, 37.50), "lon": (56.50, 61.50)},
    "Semnan / سمنان":                           {"lat": (34.50, 37.30), "lon": (52.00, 57.00)},
    "Tehran / تهران":                           {"lat": (35.30, 36.40), "lon": (50.70, 52.00)},
    "Alborz / البرز":                           {"lat": (35.70, 36.30), "lon": (50.50, 51.50)},
    "Qazvin / قزوین":                           {"lat": (35.60, 36.80), "lon": (48.80, 50.60)},
    "Zanjan / زنجان":                           {"lat": (35.60, 37.30), "lon": (47.10, 49.50)},
    "Hamadan / همدان":                          {"lat": (34.20, 35.70), "lon": (47.70, 49.50)},
    "Markazi / مرکزی":                          {"lat": (33.60, 35.50), "lon": (48.50, 51.00)},
    "Isfahan / اصفهان":                         {"lat": (31.00, 34.50), "lon": (50.00, 55.50)},
    "Yazd / یزد":                               {"lat": (29.50, 34.00), "lon": (52.50, 58.00)},
    "Kerman / کرمان":                           {"lat": (26.50, 31.50), "lon": (54.50, 60.00)},
    "Hormozgan / هرمزگان":                      {"lat": (25.50, 28.50), "lon": (52.50, 59.50)},
    "Bushehr / بوشهر":                          {"lat": (27.20, 30.30), "lon": (50.00, 53.00)},
    "Khuzestan / خوزستان":                      {"lat": (29.50, 33.00), "lon": (47.50, 51.00)},
    "Sistan & Baluchestan / سیستان و بلوچستان": {"lat": (25.00, 31.50), "lon": (58.50, 63.30)},
    "South Khorasan / خراسان جنوبی":            {"lat": (31.00, 34.50), "lon": (56.50, 61.00)},
    "Qom / قم":                                 {"lat": (34.20, 35.20), "lon": (50.20, 51.70)},
}


def get_province(lat: float, lon: float) -> str:
    """Reverse-geocode a coordinate to the nearest Iranian province (ostan)."""
    for name, bounds in PROVINCE_BOUNDS.items():
        if bounds["lat"][0] <= lat <= bounds["lat"][1] and bounds["lon"][0] <= lon <= bounds["lon"][1]:
            return name
    if lat > 36.0:
        return "Alborz Range / رشته کوه البرز"
    if lat > 32.0:
        return "Zagros Mountains / رشته کوه زاگرس"
    return "Southern Iran / جنوب ایران"


# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════
MOCK_FIRES = [
    {"id": 1, "latitude": 36.712, "longitude": 51.420, "frp": 124.5, "confidence": 92,
     "acquisition_time": datetime.now(timezone.utc) - timedelta(hours=2), "status": "CONFIRMED",
     "temp": 41.2, "humidity": 14.5, "wind_speed": 32.4, "wind_direction": 185.0, "risk_score": 94.0,
     "product_id": None, "quicklook_url": None, "telegram_message_id": None},
    {"id": 2, "latitude": 37.258, "longitude": 49.581, "frp": 68.2, "confidence": 78,
     "acquisition_time": datetime.now(timezone.utc) - timedelta(hours=4), "status": "CONFIRMED",
     "temp": 39.5, "humidity": 18.0, "wind_speed": 22.0, "wind_direction": 170.0, "risk_score": 82.0,
     "product_id": None, "quicklook_url": None, "telegram_message_id": None},
    {"id": 3, "latitude": 36.802, "longitude": 54.461, "frp": 25.1, "confidence": 62,
     "acquisition_time": datetime.now(timezone.utc) - timedelta(minutes=45), "status": "PENDING",
     "temp": 38.0, "humidity": 21.0, "wind_speed": 18.5, "wind_direction": 110.0, "risk_score": 45.0,
     "product_id": None, "quicklook_url": None, "telegram_message_id": None},
    {"id": 4, "latitude": 33.425, "longitude": 48.271, "frp": 12.4, "confidence": 55,
     "acquisition_time": datetime.now(timezone.utc) - timedelta(hours=10), "status": "FALSE_POSITIVE",
     "temp": 36.8, "humidity": 24.5, "wind_speed": 12.0, "wind_direction": 90.0, "risk_score": 28.0,
     "product_id": None, "quicklook_url": None, "telegram_message_id": None},
    {"id": 5, "latitude": 36.650, "longitude": 51.590, "frp": 85.0, "confidence": 88,
     "acquisition_time": datetime.now(timezone.utc) - timedelta(days=2), "status": "RESOLVED",
     "temp": 40.0, "humidity": 16.0, "wind_speed": 25.0, "wind_direction": 190.0, "risk_score": 90.0,
     "product_id": None, "quicklook_url": None, "telegram_message_id": None},
]


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_fires_impl(db_url: str) -> list | None:
    """Cached database fetch."""
    try:
        client = DbClient(db_url)
        return client.get_all_fires(limit=300)
    except Exception:
        logging.getLogger("dashboard").exception("DB fetch failed")
        return None


def load_fires() -> tuple[pd.DataFrame, bool]:
    """Load fire records (DB or mock), apply spatial filter, compute provinces."""
    db_client = DbClient()
    db_configured = bool(db_client.db_url and "change-me" not in db_client.db_url)

    fires: list[dict] = []
    if db_configured:
        with st.spinner("Loading fires…"):
            result = _fetch_fires_impl(db_client.db_url)
            if result is not None:
                fires = result
            else:
                db_configured = False

    if not fires:
        fires = MOCK_FIRES
        db_configured = False

    # Spatial filter
    spatial = SpatialFilter()
    fires = [f for f in fires if spatial.is_in_forest_zone(
        float(f.get("latitude", 0)), float(f.get("longitude", 0)))]

    df = pd.DataFrame(fires)
    if not df.empty and "acquisition_time" in df.columns:
        df["acquisition_time"] = pd.to_datetime(df["acquisition_time"], utc=True)
    if not df.empty:
        df["province"] = df.apply(
            lambda r: get_province(float(r["latitude"]), float(r["longitude"])), axis=1)

    return df, db_configured


df, DB_CONNECTED = load_fires()

# ═══════════════════════════════════════════════════════════════
# VISITOR TRACKER
# ═══════════════════════════════════════════════════════════════
_VISITOR_FILE = Path(__file__).resolve().parent / "visitor_stats.json"


class _VisitorTracker:
    """Singleton visitor counter persisted to disk."""

    _instance: "_VisitorTracker | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._total, cls._instance._sessions = cls._load()
        return cls._instance

    @staticmethod
    def _load():
        try:
            if _VISITOR_FILE.exists():
                data = json.loads(_VISITOR_FILE.read_text())
                return data.get("total_visitors", 0), data.get("active_sessions", {})
        except Exception:
            pass
        return 0, {}

    @staticmethod
    def _save(total: int, sessions: dict):
        try:
            _VISITOR_FILE.write_text(json.dumps({
                "total_visitors": total,
                "active_sessions": sessions,
                "updated_at": datetime.now().isoformat(),
            }))
        except Exception:
            pass

    def track(self, session_id: str) -> tuple[int, int]:
        now = time.time()
        disk_total, disk_sessions = self._load()
        if disk_total > self._total:
            self._total = disk_total
        self._sessions.update(disk_sessions)

        # Prune sessions older than 5 minutes
        self._sessions = {s: t for s, t in self._sessions.items() if now - float(t) < 300}

        if session_id not in self._sessions:
            self._total += 1
        self._sessions[session_id] = now
        self._save(self._total, self._sessions)
        return self._total, max(1, len(self._sessions))


if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

visitor = _VisitorTracker()
TOTAL_VISITORS, ACTIVE_VISITORS = visitor.track(st.session_state["session_id"])

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
lang_choice = st.sidebar.radio(
    "Language / زبان", ["English", "فارسی"],
    index=1, key="lang_toggle", horizontal=True,
)
lang = "fa" if lang_choice == "فارسی" else "en"
t = T[lang]
dir_cls = "rtl" if lang == "fa" else "ltr"

st.sidebar.markdown(
    f"<h3 class='{dir_cls}' style='margin-bottom:0;'>{t['sidebar_title']}</h3>",
    unsafe_allow_html=True,
)

# Connection status
if DB_CONNECTED:
    st.sidebar.success(t["connected"], icon="✅")
else:
    st.sidebar.warning(t["demo_mode"], icon="⚠️")

# Visitor badge
st.sidebar.markdown(f"""
<div class="sidebar-badge {dir_cls}">
    <div class="sidebar-badge-title">📊 {t['visit_stats']}</div>
    <div class="sidebar-badge-row">🟢 <b>{t['active_visitors']}:</b> <span style="color:var(--emerald);font-weight:700;">{ACTIVE_VISITORS}</span></div>
    <div class="sidebar-badge-row">👁 <b>{t['total_visitors']}:</b> <span style="color:var(--blue);font-weight:700;">{TOTAL_VISITORS:,}</span></div>
</div>
<div style="font-size:12px;color:var(--text-dim);margin:0 4px;" class="{dir_cls}">
    {t['data_sources']}<br><br>
    {t['pipeline_info']}
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# AUTO-REFRESH — browser reload every 120 s; cache TTL keeps
# intermediate renders fresh without a full DB round-trip.
# ═══════════════════════════════════════════════════════════════
st.markdown(
    '<meta http-equiv="refresh" content="120">',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown(
    f"<h1 class='{dir_cls}'>🇮🇷 {t['main_title']}</h1>"
    f"<p class='{dir_cls}' style='color:var(--text-muted);font-size:15px;margin-top:-8px;'>{t['subtitle']}</p>",
    unsafe_allow_html=True,
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _class_for(value: str) -> str:
    """Map a semantic colour name to a CSS gradient-text class."""
    return {
        "red": "text-red", "amber": "text-amber",
        "emerald": "text-emerald", "slate": "text-slate",
        "danger": "text-danger",
    }.get(value, "text-slate")


def render_stat_card(value, label: str, color: str, *, direction: str = "ltr", sub: str = ""):
    """Render a single glass-card stat in the current column context."""
    st.markdown(f"""
    <div class="glass-card {direction}">
        <div class="stat-card-label">{label}</div>
        <div class="stat-card-value {_class_for(color)}">{value}</div>
        {f'<div class="stat-card-sub">{sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)


def render_warning_card(status: str, title: str, row: dict, direction: str):
    """Render a warning/log card."""
    bg_map = {
        "CONFIRMED": ("rgba(239,68,68,0.07)", "rgba(239,68,68,0.22)"),
        "PENDING":  ("rgba(245,158,11,0.07)", "rgba(245,158,11,0.22)"),
        "FALSE_POSITIVE": ("rgba(100,116,139,0.07)", "rgba(100,116,139,0.2)"),
        "RESOLVED": ("rgba(16,185,129,0.07)", "rgba(16,185,129,0.2)"),
    }
    bg, border = bg_map.get(status, ("rgba(100,116,139,0.07)", "rgba(100,116,139,0.2)"))

    tm = row["acquisition_time"].strftime("%Y-%m-%d %H:%M UTC") if pd.notna(row.get("acquisition_time")) else "N/A"
    risk = f"{row['risk_score']:.0f}/100" if pd.notna(row.get("risk_score")) else "N/A"
    prov = row.get("province", "—")

    st.markdown(f"""
    <div class="warn-card {direction}" style="background:{bg};border:1px solid {border};">
        <div class="warn-card-title">{title}</div>
        <div class="warn-card-detail">
            <b>{t['province']}:</b> {prov}<br>
            <b>{t['coordinates']}:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br>
            <b>{t['detection']}:</b> {tm}  ·  <b>{t['risk_score']}:</b> {risk}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# STAT ROW
# ═══════════════════════════════════════════════════════════════
active_confirmed = len(df[df["status"] == "CONFIRMED"]) if not df.empty else 0
pending_fires   = len(df[df["status"] == "PENDING"])  if not df.empty else 0
false_alarms    = len(df[df["status"] == "FALSE_POSITIVE"]) if not df.empty else 0
resolved_fires  = len(df[df["status"] == "RESOLVED"]) if not df.empty else 0

sirocco_count = 0
if not df.empty and {"temp", "wind_speed", "humidity"}.issubset(df.columns):
    active_df = df[df["status"].isin(["CONFIRMED", "PENDING"])]
    if not active_df.empty:
        sirocco_count = int(active_df[
            (active_df["temp"] > 38) &
            (active_df["humidity"] < 25) &
            (active_df["wind_speed"] > 20)
        ].shape[0])

cols = st.columns(6)
with cols[0]: render_stat_card(active_confirmed, t["stat_confirmed"], "red", direction=dir_cls)
with cols[1]: render_stat_card(pending_fires,   t["stat_pending"],   "amber", direction=dir_cls)
with cols[2]: render_stat_card(false_alarms,    t["stat_false"],     "slate", direction=dir_cls)
with cols[3]: render_stat_card(resolved_fires,  t["stat_resolved"],  "emerald", direction=dir_cls)
with cols[4]: render_stat_card(sirocco_count,   t["stat_sirocco"],   "danger", direction=dir_cls)
with cols[5]:
    render_stat_card(
        ACTIVE_VISITORS, t["active_visitors"], "emerald", direction=dir_cls,
        sub=f"{TOTAL_VISITORS:,} {t['total_visitors']}",
    )

# ═══════════════════════════════════════════════════════════════
# MAP FILTERS
# ═══════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)

STATUS_MAP = {
    "CONFIRMED":       ("🔴", t["fire_confirmed"]),
    "PENDING":         ("🟡", t["thermal_pending"]),
    "FALSE_POSITIVE":  ("⚪", t["false_alarm"]),
    "RESOLVED":        ("🟢", t["resolved_fire"]),
}

f1, f2, f3 = st.columns([2, 2, 1])

with f1:
    selected_labels = st.multiselect(
        t["filter_status"],
        options=[f"{ico} {lbl}" for ico, lbl in STATUS_MAP.values()],
        default=[f"{STATUS_MAP['CONFIRMED'][0]} {STATUS_MAP['CONFIRMED'][1]}",
                 f"{STATUS_MAP['PENDING'][0]} {STATUS_MAP['PENDING'][1]}"],
        key="map_status_v3",
    )
    # Strip emoji prefix to get the bare translated label, then map to status code
    status_filter = []
    for lb in selected_labels:
        for status_code, (ico, lbl) in STATUS_MAP.items():
            if lb == f"{ico} {lbl}":
                status_filter.append(status_code)
                break

with f2:
    available_provinces = sorted(df["province"].dropna().unique().tolist()) if not df.empty and "province" in df.columns else []
    province_filter = st.multiselect(
        t["filter_province"], options=available_provinces,
        default=[], key="map_province_v3", placeholder=t["filter_all"],
    )

with f3:
    min_frp = st.slider(t["filter_frp"], 0.0, 300.0, 0.0, 10.0, key="map_frp_v3")

# Apply filters
if not df.empty:
    df_map = df[df["status"].isin(status_filter)]
    df_map = df_map[df_map["frp"] >= min_frp]
    if province_filter:
        df_map = df_map[df_map["province"].isin(province_filter)]
else:
    df_map = pd.DataFrame()

# ═══════════════════════════════════════════════════════════════
# MAP
# ═══════════════════════════════════════════════════════════════
if df_map.empty:
    map_center = [32.0, 53.5]
    zoom_start = 6
else:
    latest = df_map.sort_values("acquisition_time", ascending=False).iloc[0]
    if pd.notna(latest["latitude"]) and pd.notna(latest["longitude"]):
        map_center = [float(latest["latitude"]), float(latest["longitude"])]
        zoom_start = 10
    else:
        map_center = [32.0, 53.5]
        zoom_start = 6

m = folium.Map(
    location=map_center, zoom_start=zoom_start,
    tiles="cartodbpositron",
)

# Forest boundary overlay
if GEOJSON_PATH.exists():
    try:
        geo = json.loads(GEOJSON_PATH.read_text())
        folium.GeoJson(
            geo,
            name="Forest Hazard Zone",
            style_function=lambda _: {
                "fillColor": "#10b981", "color": "#059669",
                "weight": 2, "fillOpacity": 0.06,
            },
        ).add_to(m)
    except Exception:
        pass

# Plot markers
COLOR_MAP = {
    "CONFIRMED":       ("#ef4444", t["fire_confirmed"]),
    "PENDING":         ("#f59e0b", t["thermal_pending"]),
    "FALSE_POSITIVE":  ("#64748b", t["false_alarm"]),
    "RESOLVED":        ("#10b981", t["resolved_fire"]),
}

for _, row in df_map.iterrows():
    if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
        continue

    color, status_label = COLOR_MAP.get(row["status"], ("#64748b", row["status"]))
    tm = row["acquisition_time"].strftime("%Y-%m-%d %H:%M UTC") if pd.notna(row["acquisition_time"]) else "N/A"
    prov = row.get("province", "—")
    temp_s = f"{row['temp']:.1f} °C" if pd.notna(row.get("temp")) else "—"
    hum_s  = f"{row['humidity']:.1f}%"  if pd.notna(row.get("humidity")) else "—"
    wind_s = f"{row['wind_speed']:.1f} km/h" if pd.notna(row.get("wind_speed")) else "—"
    risk_s = f"{row['risk_score']:.0f}/100" if pd.notna(row.get("risk_score")) else "—"

    # Build popup
    popup = f"""
    <div style="font-family:'Outfit','Vazirmatn',sans-serif;width:220px;color:#1e293b;">
        <h4 style="margin:0 0 4px;color:#b91c1c;">{status_label}</h4>
        <hr style="margin:4px 0;border:0;border-top:1px solid #cbd5e1;">
        <b>{t['province']}:</b> {prov}<br>
        <b>{t['coordinates']}:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br>
        <b>{t['frp']}:</b> {row['frp']:.1f} MW<br>
        <b>{t['confidence']}:</b> {row['confidence']}%<br>
        <b>{t['time']}:</b> {tm}<br>
        <hr style="margin:4px 0;border:0;border-top:1px dashed #cbd5e1;">
        {t['temp']}: {temp_s}  ·  {t['humidity']}: {hum_s}<br>
        {t['wind']}: {wind_s}  ·  {t['risk']}: {risk_s}
    """

    # Quicklook image
    if "quicklook_url" in row and pd.notna(row.get("quicklook_url")) and row["quicklook_url"]:
        ql = str(row["quicklook_url"])
        img_uri = None
        if not ql.startswith("http"):
            lp = Path(ql)
            if lp.exists():
                try:
                    b64 = base64.b64encode(lp.read_bytes()).decode()
                    ext = lp.suffix.lower().lstrip(".")
                    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
                    img_uri = f"data:{mime};base64,{b64}"
                except Exception:
                    pass
        else:
            img_uri = ql
        if img_uri:
            popup += f"""
            <hr style="margin:4px 0;border:0;border-top:1px solid #cbd5e1;">
            <b>{t['sentinel_quicklook']}:</b><br>
            <img src="{img_uri}" style="width:100%;border-radius:6px;margin-top:4px;border:1px solid #94a3b8;">
            """

    popup += "</div>"
    clean = popup.replace("\n", "").replace("'", "&#39;")

    radius = 8 if row["status"] == "CONFIRMED" else (5 if row["status"] == "RESOLVED" else 6)
    opacity = 0.35 if row["status"] == "RESOLVED" else 0.65

    folium.CircleMarker(
        location=[float(row["latitude"]), float(row["longitude"])],
        radius=radius,
        color=color, fill=True, fill_color=color,
        fill_opacity=opacity,
        popup=folium.Popup(clean, max_width=260),
    ).add_to(m)

map_html = m._repr_html_()  # type: ignore[attr-defined]
map_html = re.sub(r'(?<!\\)\\([0-9])', r'\\\\\1', map_html)
components.html(map_html, height=620, scrolling=False)

# ═══════════════════════════════════════════════════════════════
# WARNINGS
# ═══════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)

w1, w2, w3 = st.columns([2, 2, 2])
with w1:
    st.markdown(f"<h3 class='{dir_cls}'>{t['warnings_title']}</h3>", unsafe_allow_html=True)
with w2:
    if not df_map.empty and "acquisition_time" in df_map.columns:
        min_d = df_map["acquisition_time"].min().date()
        max_d = df_map["acquisition_time"].max().date()
        date_range = st.date_input(t["date_range"], value=(min_d, max_d),
                                   min_value=min_d, max_value=max_d, key="warn_date")
    else:
        date_range = None
with w3:
    warn_provinces = sorted(df_map["province"].dropna().unique().tolist()) if not df_map.empty and "province" in df_map.columns else []
    warn_province_sel = st.multiselect(
        t["filter_province"], options=warn_provinces,
        default=[], key="warn_province", placeholder=t["filter_all"],
    )

df_w = df_map.copy()

if not df_w.empty and date_range and len(date_range) == 2:
    start = pd.Timestamp.combine(date_range[0], dt_time.min).tz_localize("UTC")
    end   = pd.Timestamp.combine(date_range[1], dt_time.max).tz_localize("UTC")
    df_w = df_w[(df_w["acquisition_time"] >= start) & (df_w["acquisition_time"] <= end)]

if not df_w.empty and warn_province_sel:
    df_w = df_w[df_w["province"].isin(warn_province_sel)]

if df_w.empty:
    st.info(t["no_data"], icon="ℹ️")
else:
    df_w = df_w.sort_values("acquisition_time", ascending=False)
    warn_cols = st.columns(2)
    for i, (_, row) in enumerate(df_w.iterrows()):
        status = row["status"]
        icon = STATUS_MAP.get(status, ("", ""))[0]
        lbl = STATUS_MAP.get(status, ("", status))[1]
        title = f"{icon} {lbl}"
        if status == "CONFIRMED":
            title += f" — FRP {row['frp']:.1f} MW"
        with warn_cols[i % 2]:
            render_warning_card(status, title, row, dir_cls)

# ═══════════════════════════════════════════════════════════════
# CITIZEN VERIFICATION FORM
# ═══════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown(f"<h3 class='{dir_cls}'>📢 {t['verification_title']}</h3>", unsafe_allow_html=True)
st.markdown(
    f"<p class='{dir_cls}' style='color:var(--text-muted);font-size:14px;margin-top:-4px;'>{t['verification_subtitle']}</p>",
    unsafe_allow_html=True,
)

with st.expander("📝 " + t["submit_report"], expanded=False):
    c1, c2 = st.columns(2)
    reporter_label_map = {
        t["citizen"]:   "Citizen",
        t["ranger"]:    "Ranger",
        t["fire_dept"]: "Fire Department",
    }
    severity_label_map = {
        t["severity_smoke"]:   "Active Smoke Plume",
        t["severity_flames"]:  "Visible Flames Spreading",
        t["severity_ext"]:     "Extinguished",
    }

    with c1:
        reporter_type = st.selectbox(
            t["reporter_label"],
            list(reporter_label_map.keys()),
            key="cit_reporter_type",
        )
        reporter_name = st.text_input(t["reporter_name"], key="cit_reporter_name")
        severity = st.selectbox(
            t["severity_label"],
            list(severity_label_map.keys()),
            key="cit_severity",
        )

    with c2:
        loc_method = st.radio(
            t["loc_method"],
            [t["gps_auto"], t["manual_coords"]],
            key="cit_loc_method",
        )

        if loc_method == t["gps_auto"]:
            st.markdown(
                f"<span style='font-size:13px;color:var(--emerald);' class='{dir_cls}'>📍 GPS Auto‑Detect Active</span>",
                unsafe_allow_html=True,
            )
            components.html("""
            <div style="font-family:system-ui,sans-serif;font-size:12px;color:var(--emerald);margin:4px 0 12px;">
                <button onclick="getLocation()" style="background:#10b981;color:white;border:none;padding:6px 14px;border-radius:8px;cursor:pointer;font-weight:600;">
                    🎯 Fetch GPS
                </button>
                <span id="gps_status" style="margin-left:10px;color:#94a3b8;">Click to detect location</span>
                <script>
                function getLocation(){
                    var s=document.getElementById("gps_status");
                    if(navigator.geolocation){s.innerText="Locating…";navigator.geolocation.getCurrentPosition(function(p){s.innerText="Lat: "+p.coords.latitude.toFixed(5)+", Lon: "+p.coords.longitude.toFixed(5);},function(e){s.innerText="Error: "+e.message;});}
                    else{s.innerText="Geolocation not supported.";}
                }
                </script>
            </div>""", height=55)
            rep_lat = st.number_input("Latitude", value=36.7120, format="%.4f", key="cit_gps_lat")
            rep_lon = st.number_input("Longitude", value=51.4200, format="%.4f", key="cit_gps_lon")
            selected_province_name = "Mazandaran / مازندران"
        else:
            selected_province_name = st.selectbox(
                t["filter_province"],
                list(PROVINCE_BOUNDS.keys()),
                key="cit_province_select",
            )
            bounds = PROVINCE_BOUNDS[selected_province_name]
            rep_lat = st.number_input(
                "Latitude",
                value=(bounds["lat"][0] + bounds["lat"][1]) / 2,
                format="%.4f", key="cit_man_lat",
            )
            rep_lon = st.number_input(
                "Longitude",
                value=(bounds["lon"][0] + bounds["lon"][1]) / 2,
                format="%.4f", key="cit_man_lon",
            )

    description = st.text_area(
        t["desc_label"],
        placeholder="E.g. Smoke plume visible near forest boundary moving North…",
        key="cit_desc",
    )

    st.markdown(f"**📷 {t['photos_required']}**")
    pc1, pc2 = st.columns(2)
    with pc1:
        uploaded_file = st.file_uploader(t["upload_photo"], type=["jpg", "jpeg", "png"], key="cit_file")
    with pc2:
        camera_file = st.camera_input(t["take_snapshot"], key="cit_cam")

    final_photo = uploaded_file or camera_file

    if st.button("🚀 " + t["submit_report"], key="cit_submit_btn", use_container_width=True):
        if not final_photo:
            st.error(t["report_err_photo"])
        else:
            try:
                photo_bytes = final_photo.getvalue()
                b64_photo = base64.b64encode(photo_bytes).decode()
                mime = "image/png" if getattr(final_photo, "name", "").endswith(".png") else "image/jpeg"

                db_client = DbClient()
                report_id = db_client.save_citizen_report({
                    "latitude": rep_lat,
                    "longitude": rep_lon,
                    "reporter_type": reporter_label_map[reporter_type],
                    "reporter_name": reporter_name or "Anonymous",
                    "wilaya": selected_province_name,
                    "severity": severity_label_map[severity],
                    "description": description,
                    "photo_b64": f"data:{mime};base64,{b64_photo}",
                    "verified": reporter_label_map[reporter_type] in ("Ranger", "Fire Department"),
                })
                st.success(t["report_success"].format(id=report_id or "SAVED"))
            except Exception as exc:
                st.error(t["report_err_general"].format(err=exc))

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown(
    f"<p class='footer {dir_cls}'>🔥 {t['footer']}</p>",
    unsafe_allow_html=True,
)
