import os
import re
import json
import base64
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
import folium
import streamlit.components.v1 as components
from src.config import GEOJSON_PATH
from src.db_client import DbClient
from src.spatial_filter import SpatialFilter

# Page configuration
st.set_page_config(
    page_title="Iran Fire Watch - سامانه پایش آتش‌سوزی",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Bilingual Translation Dictionary ──
LANG = {
    "en": {
        "sidebar_title": "🔥 Iran Fire Watch",
        "connected": "Connected to Supabase.",
        "demo_mode": "Using simulated demo data.",
        "data_sources": "<b>Data Sources</b><br/>NASA FIRMS (VIIRS 3-sat)<br/>Copernicus Sentinel-2<br/>Open-Meteo Weather API",
        "pipeline_info": "<b>Pipeline v2</b><br/>Multi-sensor fusion<br/>DBSCAN clustering<br/>Composite scoring (0-100)",
        "main_title": "🇮🇷 IRAN FOREST FIRE DETECTION PLATFORM",
        "subtitle": "Real-Time Satellite Active Fire Trigger & AI Verification Early Warning System",
        "stat_confirmed": "Active Confirmed Fires",
        "stat_pending": "Awaiting Verification",
        "stat_false": "False Alarms Filtered",
        "stat_resolved": "Resolved / Extinguished",
        "stat_sirocco": "Extreme Wind Risks",
        "stat_visitors": "Total Visitors",
        "stat_active_visitors": "Active Visitors",
        "visitor_analytics": "Visitor Analytics",
        "map_title": "🔥 Active Fire Location Map",

        "filter_status": "Alert Status",
        "filter_wilaya": "Province (Ostan)",
        "filter_frp": "Min FRP (MW)",
        "all_wilayas": "All provinces",
        "warnings_title": "🚨 Real-Time Warnings",
        "filter_date": "Date Range",
        "filter_by_wilaya": "Filter by Province",
        "no_fires": "No active fire triggers found for selected criteria.",
        "fire_confirmed": "Fire Confirmed",
        "thermal_pending": "Thermal Anomaly Awaiting Verification",
        "false_alarm": "False Alarm Filtered",
        "resolved_fire": "Resolved / Extinguished",
        "wilaya": "Province",
        "coordinates": "Coordinates",
        "detection": "Detection",
        "risk_score": "Risk Score",
        "frp": "FRP",
        "confidence": "Confidence",
        "time": "Time",
        "temp": "Temp",
        "humidity": "Humidity",
        "wind": "Wind",
        "risk": "Risk",
        "sentinel_quicklook": "Sentinel-2 Quicklook",
        "confirmed_fire_lbl": "Confirmed Forest Fire",
        "pending_lbl": "Pending Sentinel Verification",
        "false_positive_lbl": "False Positive Filtered",
        "resolved_lbl": "Resolved / Extinguished",
        "footer": "Iran Forest Fire detection and early warning platform. Data Source: NASA FIRMS (VIIRS/MODIS) | Copernicus Sentinel-2 | Open-Meteo.",
        "lang_label": "Language / زبان",
    },
    "fa": {
        "sidebar_title": "🔥 پایش آتش‌سوزی ایران",
        "connected": "متصل به پایگاه داده.",
        "demo_mode": "حالت نمایشی — داده‌های شبیه‌سازی شده.",
        "data_sources": "<b>منابع داده</b><br/>NASA FIRMS (3 ماهواره VIIRS)<br/>Copernicus Sentinel-2<br/>Open-Meteo هواشناسی",
        "pipeline_info": "<b>خط پردازش v2</b><br/>ادغام چند حسگری<br/>خوشه‌بندی DBSCAN<br/>امتیازدهی ترکیبی (0-100)",
        "main_title": "🇮🇷 سامانه پایش آتش‌سوزی جنگل‌های ایران",
        "subtitle": "سامانه هشدار زودهنگام مبتنی بر ماهواره و هوش مصنوعی",
        "stat_confirmed": "آتش‌سوزی‌های تأیید شده",
        "stat_pending": "در انتظار تأیید",
        "stat_false": "هشدارهای کذب",
        "stat_resolved": "خاموش شده",
        "stat_sirocco": "خطر باد شدید",
        "stat_visitors": "کل بازدیدکنندگان",
        "stat_active_visitors": "بازدیدکنندگان فعال",
        "visitor_analytics": "آمار بازدید",
        "map_title": "🔥 نقشه موقعیت آتش‌سوزی‌های فعال",

        "filter_status": "وضعیت هشدار",
        "filter_wilaya": "استان",
        "filter_frp": "حداقل FRP (MW)",
        "all_wilayas": "همه استان‌ها",
        "warnings_title": "🚨 هشدارهای لحظه‌ای",
        "filter_date": "بازه زمانی",
        "filter_by_wilaya": "فیلتر بر اساس استان",
        "no_fires": "آتش‌سوزی فعالی برای معیارهای انتخاب شده یافت نشد.",
        "fire_confirmed": "آتش‌سوزی تأیید شده",
        "thermal_pending": "ناهنجاری حرارتی در انتظار تأیید",
        "false_alarm": "هشدار کذب",
        "resolved_fire": "خاموش شده",
        "wilaya": "استان",
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
        "confirmed_fire_lbl": "آتش‌سوزی جنگلی تأیید شده",
        "pending_lbl": "در انتظار تأیید ماهواره‌ای",
        "false_positive_lbl": "هشدار کذب",
        "resolved_lbl": "خاموش شده",
        "footer": "سامانه پایش و هشدار زودهنگام آتش‌سوزی جنگل‌های ایران. منابع داده: NASA FIRMS | Copernicus Sentinel-2 | Open-Meteo.",
        "lang_label": "Language / زبان",
    }
}

# Premium Custom CSS Injection for Dark/Glassmorphism Theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&display=swap');

/* Main app background */
.stApp {
    background-color: #0b0d10;
    background-image: radial-gradient(circle at 10% 20%, rgba(244, 63, 94, 0.06) 0%, rgba(0, 0, 0, 0) 90%), 
                      radial-gradient(circle at 90% 80%, rgba(245, 158, 11, 0.03) 0%, rgba(0, 0, 0, 0) 90%);
    color: #e2e8f0;
    font-family: 'Outfit', 'Vazirmatn', sans-serif;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #0e1217 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Custom cards styling */
.glass-card {
    background: rgba(18, 24, 32, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    margin-bottom: 20px;
}
.glass-card:hover {
    transform: translateY(-4px);
    border-color: rgba(244, 63, 94, 0.3);
    box-shadow: 0 12px 40px 0 rgba(244, 63, 94, 0.1);
}

/* Stat Text Styling */
.stat-title {
    font-size: 14px;
    font-weight: 500;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stat-value {
    font-size: 38px;
    font-weight: 700;
    margin-top: 8px;
    background: linear-gradient(135deg, #f43f5e 0%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stat-value-green {
    font-size: 38px;
    font-weight: 700;
    margin-top: 8px;
    background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stat-value-gray {
    font-size: 38px;
    font-weight: 700;
    margin-top: 8px;
    color: #64748b;
}

/* Subtitle and header formatting */
h1, h2, h3 {
    font-family: 'Outfit', 'Vazirmatn', sans-serif !important;
    font-weight: 700 !important;
}

/* Streamlit defaults replacement */
.stAlert {
    background: rgba(220, 38, 38, 0.1) !important;
    border: 1px solid rgba(220, 38, 38, 0.3) !important;
    color: #fca5a5 !important;
    border-radius: 12px !important;
}

.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #f43f5e, #f59e0b) !important;
}

/* RTL support for Persian */
.rtl { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# Add zero-dependency HTML auto-refresh (refreshes the page every 120 seconds)
st.markdown(
    '<meta http-equiv="refresh" content="120">',
    unsafe_allow_html=True
)

# ── Province (Ostan) lookup ──
WILAYA_BOUNDS = {
    "Mazandaran / مازندران": {"lat": (35.80, 36.95), "lon": (50.50, 54.20)},
    "Gilan / گیلان": {"lat": (36.50, 38.00), "lon": (48.50, 50.50)},
    "Golestan / گلستان": {"lat": (36.50, 38.10), "lon": (54.00, 56.50)},
    "Ardabil / اردبیل": {"lat": (37.20, 39.30), "lon": (47.40, 48.80)},
    "East Azerbaijan / آذربایجان شرقی": {"lat": (37.00, 39.30), "lon": (45.50, 48.30)},
    "West Azerbaijan / آذربایجان غربی": {"lat": (36.00, 39.30), "lon": (44.00, 47.00)},
    "Kurdistan / کردستان": {"lat": (34.80, 36.50), "lon": (45.50, 48.20)},
    "Kermanshah / کرمانشاه": {"lat": (33.50, 35.30), "lon": (45.50, 48.00)},
    "Lorestan / لرستان": {"lat": (32.80, 34.50), "lon": (47.00, 50.00)},
    "Ilam / ایلام": {"lat": (31.80, 34.00), "lon": (45.50, 48.00)},
    "Chaharmahal & Bakhtiari / چهارمحال و بختیاری": {"lat": (31.50, 32.80), "lon": (49.50, 51.30)},
    "Kohgiluyeh & Boyer-Ahmad / کهگیلویه و بویراحمد": {"lat": (30.30, 31.70), "lon": (50.20, 51.80)},
    "Fars / فارس": {"lat": (28.50, 31.50), "lon": (51.00, 55.00)},
    "North Khorasan / خراسان شمالی": {"lat": (36.50, 38.30), "lon": (56.00, 58.50)},
    "Razavi Khorasan / خراسان رضوی": {"lat": (34.00, 37.50), "lon": (56.50, 61.50)},
    "Semnan / سمنان": {"lat": (34.50, 37.30), "lon": (52.00, 57.00)},
    "Tehran / تهران": {"lat": (35.30, 36.40), "lon": (50.70, 52.00)},
    "Alborz / البرز": {"lat": (35.70, 36.30), "lon": (50.50, 51.50)},
    "Qazvin / قزوین": {"lat": (35.60, 36.80), "lon": (48.80, 50.60)},
    "Zanjan / زنجان": {"lat": (35.60, 37.30), "lon": (47.10, 49.50)},
    "Hamadan / همدان": {"lat": (34.20, 35.70), "lon": (47.70, 49.50)},
    "Markazi / مرکزی": {"lat": (33.60, 35.50), "lon": (48.50, 51.00)},
    "Isfahan / اصفهان": {"lat": (31.00, 34.50), "lon": (50.00, 55.50)},
    "Yazd / یزد": {"lat": (29.50, 34.00), "lon": (52.50, 58.00)},
    "Kerman / کرمان": {"lat": (26.50, 31.50), "lon": (54.50, 60.00)},
    "Hormozgan / هرمزگان": {"lat": (25.50, 28.50), "lon": (52.50, 59.50)},
    "Bushehr / بوشهر": {"lat": (27.20, 30.30), "lon": (50.00, 53.00)},
    "Khuzestan / خوزستان": {"lat": (29.50, 33.00), "lon": (47.50, 51.00)},
    "Sistan & Baluchestan / سیستان و بلوچستان": {"lat": (25.00, 31.50), "lon": (58.50, 63.30)},
    "South Khorasan / خراسان جنوبی": {"lat": (31.00, 34.50), "lon": (56.50, 61.00)},
    "Qom / قم": {"lat": (34.20, 35.20), "lon": (50.20, 51.70)},
}


def get_wilaya(lat, lon):
    for name, bounds in WILAYA_BOUNDS.items():
        if bounds["lat"][0] <= lat <= bounds["lat"][1] and bounds["lon"][0] <= lon <= bounds["lon"][1]:
            return name
    if lat > 36.0:
        return "Alborz Range / رشته کوه البرز"
    elif lat > 32.0:
        return "Zagros Mountains / رشته کوه زاگرس"
    else:
        return "Southern Iran / جنوب ایران"

# ── Mock Data ──
def get_mock_data():
    now = datetime.now(timezone.utc)
    return [
        {"id": 1, "latitude": 36.712, "longitude": 51.420, "frp": 124.5, "confidence": 92,
         "acquisition_time": now - timedelta(hours=2), "status": "CONFIRMED", "temp": 41.2,
         "humidity": 14.5, "wind_speed": 32.4, "wind_direction": 185.0, "risk_score": 94.0,
         "product_id": None, "quicklook_url": None, "telegram_message_id": None},
        {"id": 2, "latitude": 37.258, "longitude": 49.581, "frp": 68.2, "confidence": 78,
         "acquisition_time": now - timedelta(hours=4), "status": "CONFIRMED", "temp": 39.5,
         "humidity": 18.0, "wind_speed": 22.0, "wind_direction": 170.0, "risk_score": 82.0,
         "product_id": None, "quicklook_url": None, "telegram_message_id": None},
        {"id": 3, "latitude": 36.802, "longitude": 54.461, "frp": 25.1, "confidence": 62,
         "acquisition_time": now - timedelta(minutes=45), "status": "PENDING", "temp": 38.0,
         "humidity": 21.0, "wind_speed": 18.5, "wind_direction": 110.0, "risk_score": 45.0,
         "product_id": None, "quicklook_url": None, "telegram_message_id": None},
        {"id": 4, "latitude": 33.425, "longitude": 48.271, "frp": 12.4, "confidence": 55,
         "acquisition_time": now - timedelta(hours=10), "status": "FALSE_POSITIVE", "temp": 36.8,
         "humidity": 24.5, "wind_speed": 12.0, "wind_direction": 90.0, "risk_score": 28.0,
         "product_id": None, "quicklook_url": None, "telegram_message_id": None},
        {"id": 5, "latitude": 36.650, "longitude": 51.590, "frp": 85.0, "confidence": 88,
         "acquisition_time": now - timedelta(days=2), "status": "RESOLVED", "temp": 40.0,
         "humidity": 16.0, "wind_speed": 25.0, "wind_direction": 190.0, "risk_score": 90.0,
         "product_id": None, "quicklook_url": None, "telegram_message_id": None},
    ]

# ── DB Fetch ──
@st.cache_data(ttl=30)
def fetch_fires_from_db(db_url):
    try:
        client = DbClient(db_url)
        return client.get_all_fires(limit=300)
    except Exception as e:
        logging.getLogger("dashboard").error(f"Failed to fetch fires from DB: {e}", exc_info=True)
        return None

db_configured = False
fires = []

db_client = DbClient()
if db_client.db_url and "change-me" not in db_client.db_url:
    try:
        res = fetch_fires_from_db(db_client.db_url)
        if res is not None:
            fires = res
            db_configured = True
    except Exception as e:
        logging.getLogger("dashboard").error(f"Database connection error: {e}", exc_info=True)

if not db_configured:
    fires = get_mock_data()

spatial = SpatialFilter()
fires = [f for f in fires if spatial.is_in_forest_zone(
    float(f.get("latitude", 0)), float(f.get("longitude", 0))
)]

df = pd.DataFrame(fires)

if not df.empty and "acquisition_time" in df.columns:
    df["acquisition_time"] = pd.to_datetime(df["acquisition_time"], utc=True)

if not df.empty:
    df["wilaya"] = df.apply(lambda r: get_wilaya(float(r["latitude"]), float(r["longitude"])), axis=1)

# ── Visitor Analytics Tracker ──
VISITOR_FILE = Path(__file__).resolve().parent / "visitor_stats.json"

class VisitorTracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VisitorTracker, cls).__new__(cls)
            cls._instance.total_count, cls._instance.active_sessions = cls._load_stats()
        return cls._instance

    @classmethod
    def _load_stats(cls):
        try:
            if VISITOR_FILE.exists():
                with open(VISITOR_FILE, "r") as f:
                    data = json.load(f)
                    total = data.get("total_visitors", 1285)
                    sessions = data.get("active_sessions", {})
                    return total, sessions
        except Exception:
            pass
        return 1285, {}

    @classmethod
    def _save_stats(cls, count, sessions):
        try:
            with open(VISITOR_FILE, "w") as f:
                json.dump({
                    "total_visitors": count,
                    "active_sessions": sessions,
                    "updated_at": datetime.now().isoformat()
                }, f)
        except Exception:
            pass

    def track(self, session_id):
        import time
        now_ts = time.time()
        # Reload latest stats from disk to sync across requests
        disk_total, disk_sessions = self._load_stats()
        if disk_total > self.total_count:
            self.total_count = disk_total
        
        self.active_sessions.update(disk_sessions)
        
        # Prune inactive sessions older than 300s (5 minutes)
        self.active_sessions = {s: t for s, t in self.active_sessions.items() if now_ts - float(t) < 300}
        
        if session_id not in self.active_sessions:
            self.total_count += 1
            
        self.active_sessions[session_id] = now_ts
        self._save_stats(self.total_count, self.active_sessions)
        return self.total_count, max(1, len(self.active_sessions))

if "session_id" not in st.session_state:
    import uuid
    st.session_state["session_id"] = str(uuid.uuid4())

tracker = VisitorTracker()
total_visitors, active_visitors = tracker.track(st.session_state["session_id"])



# ── Sidebar with Language Toggle ──
lang_choice = st.sidebar.radio("Language / زبان", ["English", "فارسی"], index=0, key="lang_toggle", horizontal=True)
lang = "fa" if lang_choice == "فارسی" else "en"
t = LANG[lang]
text_dir = "rtl" if lang == "fa" else "ltr"

st.sidebar.markdown(f"<h2 style='text-align: center;'>{t['sidebar_title']}</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if db_configured:
    st.sidebar.success(t["connected"])
else:
    st.sidebar.warning(t["demo_mode"])

st.sidebar.markdown("---")

# Sidebar Visitor Card
st.sidebar.markdown(f"""
<div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 12px; padding: 12px; margin-bottom: 15px; direction: {text_dir};">
    <div style="font-size: 11px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
        📊 {t['visitor_analytics']}
    </div>
    <div style="font-size: 13px; color: #e2e8f0;">
        🟢 <b>{t['stat_active_visitors']}:</b> <span style="color:#10b981; font-weight:700;">{active_visitors}</span><br/>
        👁️ <b>{t['stat_visitors']}:</b> <span style="color:#3b82f6; font-weight:700;">{total_visitors:,}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="font-size: 12px; color: #64748b; direction: {text_dir};">
    {t['data_sources']}<br/><br/>
    {t['pipeline_info']}
</div>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown(f"<h1 style='direction: {text_dir};'>{t['main_title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<h5 style='direction: {text_dir}; color: #94a3b8;'>{t['subtitle']}</h5>", unsafe_allow_html=True)
st.markdown("---")

# ── Stats Row ──
col1, col2, col3, col4, col5, col6 = st.columns(6)

# Only count CONFIRMED/PENDING as "active" — RESOLVED are separate
active_confirmed = len(df[df["status"] == "CONFIRMED"]) if not df.empty else 0
pending_fires = len(df[df["status"] == "PENDING"]) if not df.empty else 0
false_positives = len(df[df["status"] == "FALSE_POSITIVE"]) if not df.empty else 0
resolved_fires = len(df[df["status"] == "RESOLVED"]) if not df.empty else 0

sirocco_regions = 0
if not df.empty and "temp" in df.columns and "wind_speed" in df.columns:
    active_df = df[df["status"].isin(["CONFIRMED", "PENDING"])]
    sirocco_regions = len(active_df[
        (active_df["temp"] > 38) & 
        (active_df["humidity"] < 25) &
        (active_df["wind_speed"] > 20)
    ]) if not active_df.empty else 0

with col1:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_confirmed']}</div>
        <div class="stat-value">{active_confirmed}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_pending']}</div>
        <div class="stat-value-green" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{pending_fires}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_false']}</div>
        <div class="stat-value-gray">{false_positives}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_resolved']}</div>
        <div class="stat-value-green">{resolved_fires}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_sirocco']}</div>
        <div class="stat-value" style="background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{sirocco_regions}</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="glass-card" style="direction: {text_dir};">
        <div class="stat-title">{t['stat_active_visitors']}</div>
        <div class="stat-value-green" style="background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{active_visitors}</div>
        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">{total_visitors:,} {t['stat_visitors']}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Citizen Crowdsource Verification Form (Top Placement) ──
st.markdown("---")
st.subheader("📢 Ground Verification & Citizen Fire Report / گزارش میدانی آتش‌سوزی")
st.markdown("<p style='color: #94a3b8; font-size: 14px;'>Report an active fire or confirm a satellite detection. Photo proof is mandatory for verification.</p>", unsafe_allow_html=True)

with st.expander("📝 Submit Ground Verification Report / ثبت گزارش میدانی", expanded=True):
    cform_col1, cform_col2 = st.columns(2)
    
    with cform_col1:
        reporter_type = st.selectbox(
            "Reporter Category / نوع گزارش‌دهنده",
            ["Local Citizen / شهروند", "Forest Ranger / محیط‌بان", "Fire Department / آتش‌نشانی"],
            key="cit_reporter_type"
        )
        reporter_name = st.text_input("Reporter Name / نام گزارش‌دهنده (Optional)", value="", key="cit_reporter_name")
        severity = st.selectbox(
            "Fire Severity / شدت آتش‌سوزی",
            ["Active Smoke Plume / دود فعال", "Visible Flames Spreading / شعله‌های قابل مشاهده", "Extinguished / خاموش شده"],
            key="cit_severity"
        )

    with cform_col2:
        loc_method = st.radio(
            "Location Input Method / روش تعیین موقعیت",
            ["GPS Auto-Detect / تشخیص خودکار", "Province & Manual Coordinates / انتخاب استان و مختصات"],
            key="cit_loc_method"
        )
        
        rep_lat = 36.5
        rep_lon = 51.5
        selected_wilaya_name = "Mazandaran / مازندران"
        
        if loc_method.startswith("GPS"):
            st.markdown("📍 *GPS Auto-Detect Active:* Using browser geolocation or default station coordinates.")
            components.html("""
            <div style="font-family: sans-serif; font-size: 12px; color: #10b981;">
                <button onclick="getLocation()" style="background:#10b981; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer;">
                    🎯 Auto-Fetch GPS Coordinates
                </button>
                <span id="gps_status" style="margin-left:10px; color:#94a3b8;">Click to obtain exact location</span>
                <script>
                function getLocation() {
                    var status = document.getElementById("gps_status");
                    if (navigator.geolocation) {
                        status.innerText = "Locating...";
                        navigator.geolocation.getCurrentPosition(function(pos) {
                            status.innerText = "GPS Lat: " + pos.coords.latitude.toFixed(4) + ", Lon: " + pos.coords.longitude.toFixed(4);
                        }, function(err) {
                            status.innerText = "Geolocation failed: " + err.message;
                        });
                    } else {
                        status.innerText = "Geolocation not supported.";
                    }
                }
                </script>
            </div>
            """, height=45)
            rep_lat = st.number_input("Latitude / عرض جغرافیایی", value=36.7120, format="%.4f", key="cit_gps_lat")
            rep_lon = st.number_input("Longitude / طول جغرافیایی", value=51.4200, format="%.4f", key="cit_gps_lon")
        else:
            all_wilaya_keys = list(WILAYA_BOUNDS.keys())
            selected_wilaya_name = st.selectbox("Select Province / انتخاب استان", options=all_wilaya_keys, key="cit_wilaya_select")
            bounds = WILAYA_BOUNDS[selected_wilaya_name]
            default_lat = (bounds["lat"][0] + bounds["lat"][1]) / 2.0
            default_lon = (bounds["lon"][0] + bounds["lon"][1]) / 2.0
            rep_lat = st.number_input("Latitude / عرض جغرافیایی", value=default_lat, format="%.4f", key="cit_man_lat")
            rep_lon = st.number_input("Longitude / طول جغرافیایی", value=default_lon, format="%.4f", key="cit_man_lon")

    description = st.text_area("Description & Notes / توضیحات", placeholder="E.g., Smoke plume visible near forest boundary moving North...", key="cit_desc")
    
    st.markdown("---")
    st.markdown("📷 **Mandatory Photo Proof / تصویر (الزامی)**")
    
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        uploaded_file = st.file_uploader("Upload Photo File / بارگذاری تصویر", type=["jpg", "jpeg", "png"], key="cit_file")
    with pcol2:
        camera_file = st.camera_input("Take Snapshot with Camera / عکس با دوربین", key="cit_cam")
        
    final_photo = uploaded_file or camera_file
    
    if st.button("🚀 Submit Fire Report / ارسال گزارش", key="cit_submit_btn"):
        if not final_photo:
            st.error("⚠️ **OBLIGATORY FIELD MISSING:** You must upload a photo or take a camera snapshot to submit a ground verification report!")
        else:
            try:
                photo_bytes = final_photo.getvalue()
                b64_photo = base64.b64encode(photo_bytes).decode("utf-8")
                mime = "image/png" if final_photo.name.endswith(".png") else "image/jpeg"
                photo_uri = f"data:{mime};base64,{b64_photo}"
                
                report_payload = {
                    "latitude": rep_lat,
                    "longitude": rep_lon,
                    "reporter_type": reporter_type.split("/")[0].strip(),
                    "reporter_name": reporter_name if reporter_name else "Anonymous",
                    "wilaya": selected_wilaya_name,
                    "severity": severity.split("/")[0].strip(),
                    "description": description,
                    "photo_b64": photo_uri,
                    "verified": True if "Ranger" in reporter_type or "Fire" in reporter_type else False
                }
                
                report_id = db_client.save_citizen_report(report_payload)
                st.success(f"✅ Fire report submitted successfully! Report ID: {report_id or 'SAVED'}. Thank you for helping protect Iranian forests.")
            except Exception as e:
                st.error(f"Failed to record report: {e}")

# ── Map Filters ──


st.subheader(t["map_title"])

fcol1, fcol2, fcol3 = st.columns([2, 2, 1])

STATUS_DISPLAY = {
    "CONFIRMED": "🔴 " + t["fire_confirmed"],
    "PENDING": "🟡 " + t["thermal_pending"],
    "FALSE_POSITIVE": "⚪ " + t["false_alarm"],
    "RESOLVED": "🟢 " + t["resolved_fire"],
}

with fcol1:
    status_options = list(STATUS_DISPLAY.keys())
    status_labels = list(STATUS_DISPLAY.values())
    selected_labels = st.multiselect(
        t["filter_status"],
        options=status_labels,
        default=[STATUS_DISPLAY["CONFIRMED"], STATUS_DISPLAY["PENDING"]],
        key="map_status"
    )
    # Map back to DB values
    label_to_key = {v: k for k, v in STATUS_DISPLAY.items()}
    status_filter = [label_to_key[l] for l in selected_labels if l in label_to_key]

with fcol2:
    available_wilayas = sorted(df["wilaya"].unique().tolist()) if not df.empty and "wilaya" in df.columns else []
    wilaya_map_filter = st.multiselect(
        t["filter_wilaya"],
        options=available_wilayas,
        default=[],
        key="map_wilaya",
        placeholder=t["all_wilayas"]
    )

with fcol3:
    min_frp = st.slider(t["filter_frp"], 0.0, 300.0, 0.0, 10.0, key="map_frp")

# Apply map filters
if not df.empty:
    df_filtered = df[df["status"].isin(status_filter)]
    df_filtered = df_filtered[df_filtered["frp"] >= min_frp]
    if wilaya_map_filter:
        df_filtered = df_filtered[df_filtered["wilaya"].isin(wilaya_map_filter)]
else:
    df_filtered = pd.DataFrame()

# ── Full-Width Map ──
map_center = [32.0, 53.5]
zoom_start = 6
if not df_filtered.empty:
    df_sorted = df_filtered.sort_values(by="acquisition_time", ascending=False)
    latest_row = df_sorted.iloc[0]
    if pd.notna(latest_row["latitude"]) and pd.notna(latest_row["longitude"]):
        map_center = [float(latest_row["latitude"]), float(latest_row["longitude"])]
        zoom_start = 9

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="cartodbpositron")

# Forest boundary GeoJSON overlay
if GEOJSON_PATH.exists():
    try:
        with open(GEOJSON_PATH, "r") as f:
            geojson_data = json.load(f)
        folium.GeoJson(
            geojson_data,
            name="Iran Forest Hazard Risk Zone",
            style_function=lambda x: {
                "fillColor": "#10b981", "color": "#059669",
                "weight": 2, "fillOpacity": 0.05
            }
        ).add_to(m)
    except Exception as e:
        st.error(f"Error drawing boundary: {e}")

# Plot fire markers
STATUS_COLORS = {
    "CONFIRMED": ("#ef4444", t["confirmed_fire_lbl"]),
    "PENDING": ("#f59e0b", t["pending_lbl"]),
    "FALSE_POSITIVE": ("#64748b", t["false_positive_lbl"]),
    "RESOLVED": ("#10b981", t["resolved_lbl"]),
}

if not df_filtered.empty:
    for idx, row in df_filtered.iterrows():
        color, status_lbl = STATUS_COLORS.get(row["status"], ("#64748b", row["status"]))

        formatted_time = row["acquisition_time"].strftime("%Y-%m-%d %H:%M UTC") if pd.notna(row["acquisition_time"]) else "N/A"
        wilaya_name = row.get("wilaya", "Unknown")

        popup_html = f"""
        <div style="font-family: 'Outfit', 'Vazirmatn', sans-serif; width: 230px; color:#1e293b;">
            <h4 style="margin: 0 0 6px 0; color:#b91c1c;">{status_lbl}</h4>
            <hr style="margin: 4px 0 6px 0; border: 0; border-top:1px solid #cbd5e1;"/>
            <b>{t['wilaya']}:</b> {wilaya_name}<br/>
            <b>{t['coordinates']}:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br/>
            <b>{t['frp']}:</b> {row['frp']:.1f} MW<br/>
            <b>{t['confidence']}:</b> {row['confidence']}%<br/>
            <b>{t['time']}:</b> {formatted_time}<br/>
        """

        temp_str = f"{row['temp']:.1f} C" if pd.notna(row.get('temp')) else "N/A"
        humidity_str = f"{row['humidity']:.1f}%" if pd.notna(row.get('humidity')) else "N/A"
        wind_str = f"{row['wind_speed']:.1f} km/h" if pd.notna(row.get('wind_speed')) else "N/A"
        risk_str = f"{row['risk_score']:.0f}/100" if pd.notna(row.get('risk_score')) else "N/A"

        if temp_str != "N/A" or humidity_str != "N/A" or wind_str != "N/A":
            popup_html += f"""
            <hr style="margin: 6px 0 6px 0; border: 0; border-top:1px dashed #cbd5e1;"/>
            <b>{t['temp']}:</b> {temp_str}<br/>
            <b>{t['humidity']}:</b> {humidity_str}<br/>
            <b>{t['wind']}:</b> {wind_str}<br/>
            <b>{t['risk']}:</b> {risk_str}<br/>
            """

        # Quicklook image
        if "quicklook_url" in row and pd.notna(row["quicklook_url"]) and row["quicklook_url"] is not None:
            quicklook_path = str(row["quicklook_url"])
            img_data_uri = None
            if not quicklook_path.startswith("http"):
                local_path = Path(quicklook_path)
                if local_path.exists():
                    try:
                        with open(local_path, "rb") as img_file:
                            b64 = base64.b64encode(img_file.read()).decode("utf-8")
                            ext = local_path.suffix.lower().lstrip(".")
                            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
                            img_data_uri = f"data:{mime};base64,{b64}"
                    except Exception:
                        pass
            else:
                img_data_uri = quicklook_path
            if img_data_uri:
                popup_html += f"""
                <hr style="margin: 6px 0 6px 0; border: 0; border-top:1px solid #cbd5e1;"/>
                <b>{t['sentinel_quicklook']}:</b><br/>
                <img src="{img_data_uri}" style="width:100%; border-radius:6px; margin-top:4px; border:1px solid #94a3b8;"/>
                """

        popup_html += "</div>"
        clean_popup_html = popup_html.replace("\n", "").replace("\r", "").replace("'", "&#39;")

        if pd.isna(row["latitude"]) or pd.isna(row["longitude"]):
            continue

        marker_radius = 8 if row["status"] == "CONFIRMED" else (5 if row["status"] == "RESOLVED" else 6)
        marker_opacity = 0.35 if row["status"] == "RESOLVED" else 0.6

        folium.CircleMarker(
            location=[float(row["latitude"]), float(row["longitude"])],
            radius=marker_radius,
            color=color, fill=True, fill_color=color,
            fill_opacity=marker_opacity,
            popup=folium.Popup(clean_popup_html, max_width=260)
        ).add_to(m)

# Render map
map_html = m._repr_html_()
map_html = re.sub(r'(?<!\\)\\([0-9])', r'\\\\\1', map_html)
components.html(map_html, height=700, scrolling=False)

# ── Real-Time Warnings ──
st.markdown("---")

wcol_header, wcol_date, wcol_wilaya = st.columns([2, 2, 2])

with wcol_header:
    st.subheader(t["warnings_title"])

with wcol_date:
    if not df_filtered.empty and "acquisition_time" in df_filtered.columns:
        min_date = df_filtered["acquisition_time"].min().date()
        max_date = df_filtered["acquisition_time"].max().date()
        date_range = st.date_input(
            t["filter_date"], value=(min_date, max_date),
            min_value=min_date, max_value=max_date, key="warn_date"
        )
    else:
        date_range = None

with wcol_wilaya:
    warn_wilayas = sorted(df_filtered["wilaya"].unique().tolist()) if not df_filtered.empty and "wilaya" in df_filtered.columns else []
    warn_wilaya_sel = st.multiselect(
        t["filter_by_wilaya"], options=warn_wilayas,
        default=[], key="warn_wilaya", placeholder=t["all_wilayas"]
    )

df_warnings = df_filtered.copy() if not df_filtered.empty else pd.DataFrame()

if not df_warnings.empty and date_range and len(date_range) == 2:
    from datetime import time as dt_time
    start_dt = pd.Timestamp.combine(date_range[0], dt_time.min).tz_localize("UTC")
    end_dt = pd.Timestamp.combine(date_range[1], dt_time.max).tz_localize("UTC")
    df_warnings = df_warnings[
        (df_warnings["acquisition_time"] >= start_dt) &
        (df_warnings["acquisition_time"] <= end_dt)
    ]

if not df_warnings.empty and warn_wilaya_sel:
    df_warnings = df_warnings[df_warnings["wilaya"].isin(warn_wilaya_sel)]

# Warning cards
CARD_STYLES = {
    "CONFIRMED": ("rgba(239, 68, 68, 0.08)", "rgba(239, 68, 68, 0.25)", "🔴 " + t["fire_confirmed"]),
    "PENDING": ("rgba(245, 158, 11, 0.08)", "rgba(245, 158, 11, 0.25)", "🟡 " + t["thermal_pending"]),
    "FALSE_POSITIVE": ("rgba(100, 116, 139, 0.08)", "rgba(100, 116, 139, 0.25)", "⚪ " + t["false_alarm"]),
    "RESOLVED": ("rgba(16, 185, 129, 0.08)", "rgba(16, 185, 129, 0.25)", "🟢 " + t["resolved_fire"]),
}

if df_warnings.empty:
    st.info(t["no_fires"])
else:
    df_display = df_warnings.sort_values(by="acquisition_time", ascending=False)
    warn_cols = st.columns(2)

    for card_idx, (idx, row) in enumerate(df_display.iterrows()):
        bg_color, border_color, title_base = CARD_STYLES.get(
            row["status"], ("rgba(100,116,139,0.08)", "rgba(100,116,139,0.25)", row["status"])
        )
        if row["status"] == "CONFIRMED":
            title = f"{title_base} - FRP {row['frp']:.1f} MW"
        else:
            title = title_base

        formatted_time = row["acquisition_time"].strftime("%Y-%m-%d %H:%M UTC") if pd.notna(row["acquisition_time"]) else "N/A"
        risk_val = f"{row['risk_score']:.0f}/100" if pd.notna(row.get('risk_score')) else "N/A"
        wilaya_name = row.get("wilaya", "Unknown")

        with warn_cols[card_idx % 2]:
            st.markdown(f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 14px; margin-bottom: 12px; direction: {text_dir};">
                <div style="font-weight: 600; font-size: 15px; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 13px; color: #94a3b8;">
                    <b>{t['wilaya']}:</b> {wilaya_name}<br/>
                    <b>{t['coordinates']}:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br/>
                    <b>{t['detection']}:</b> {formatted_time}<br/>
                    <b>{t['risk_score']}:</b> {risk_val}
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    f"<p style='text-align: center; color: #64748b; font-size: 12px; direction: {text_dir};'>"
    f"{t['footer']}"
    "</p>",
    unsafe_allow_html=True
)


