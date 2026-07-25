# Iran Forest Fire Detection Platform 🇮🇷🔥

A real-time forest fire early warning system for Iran, powered by NASA satellite data, AI-driven smoke verification, and automated Telegram alerts. Built for **zero-budget deployability** using entirely open data sources.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## 🌍 Overview

Iran loses thousands of hectares of forest to wildfires every summer, particularly across the Hyrcanian Caspian forests (Mazandaran, Gilan, Golestan), the Zagros oak forests, and the Arasbaran region. This platform provides **autonomous fire detection and alerting** by:

1. **Ingesting** active fire hotspots from **3 NASA VIIRS satellites** (SNPP, NOAA-20, NOAA-21) via FIRMS API
2. **Clustering** spatially proximate detections using DBSCAN to group hotspots into discrete fire events
3. **Verifying** each cluster against **Copernicus Sentinel-2** optical imagery with a computer-vision smoke detector
4. **Enriching** with live weather data (temperature, humidity, wind, drought index) from Open-Meteo
5. **Scoring** each fire with a weighted composite confidence metric (0–100)
6. **Alerting** via Telegram with annotated satellite imagery, weather context, and extreme wind warnings
7. **Visualizing** on a real-time Streamlit dashboard with interactive Leaflet maps

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Cron (30 min)                │
│                     or Local Pipeline Run                      │
└───────────────────────────┬────────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │     pipeline.py       │
                │   (Orchestrator)      │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
  ┌─────▼─────┐     ┌──────▼──────┐     ┌──────▼──────┐
  │ FIRMS API  │     │  Copernicus │     │  Open-Meteo  │
  │ (3 Sats)   │     │  Sentinel-2 │     │  Weather API │
  └─────┬──────┘     └──────┬──────┘     └──────┬──────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                ┌───────────▼───────────┐
                │  Multi-Sensor Fusion  │
                │  DBSCAN Clustering    │
                │  CV Smoke Detection   │
                │  Composite Scoring    │
                └───────────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              │                           │
     ┌────────▼────────┐        ┌────────▼────────┐
     │ Supabase/PostGIS│        │    Telegram     │
     │   (Database)    │        │  Notifications  │
     └────────┬────────┘        └─────────────────┘
              │
     ┌────────▼────────┐
     │   Streamlit     │
     │   Dashboard     │
     └─────────────────┘
```

## ✨ Key Features

| Feature | Description |
|---|---|
| **Multi-Sensor Fusion** | Merges data from SNPP, NOAA-20, and NOAA-21 VIIRS instruments for maximum coverage |
| **DBSCAN Clustering** | Groups nearby hotspots into discrete fire events (O(n log n) spatial indexing) |
| **CV Smoke Detection** | Computer-vision heuristic analyzes Sentinel-2 imagery for smoke plume signatures |
| **Composite Scoring** | Weighted confidence metric (FRP, cluster size, multi-sensor confirmation, weather risk, smoke detection) |
| **Extreme Wind Detection** | Identifies dangerous fire weather conditions (hot, dry, strong winds) that accelerate fire spread |
| **Drought Modifier** | Boosts fire risk scores when no precipitation has occurred for 5+ days |
| **Notification Dedup** | 6-hour cooldown prevents duplicate Telegram alerts for the same fire |
| **PENDING → CONFIRMED** | Intelligently upgrades existing records instead of creating duplicates |
| **Province Mapping** | Reverse-geocodes fire coordinates to Iranian provinces (ostans) |
| **Real-Time Dashboard** | Interactive Leaflet map with status, province, FRP, and date filters |

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL with PostGIS extension (or [Supabase](https://supabase.com/) free tier)
- API keys (all free):
  - [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area/) API key
  - [Telegram Bot](https://core.telegram.org/bots#botfather) token + channel ID
  - [Copernicus CDSE](https://dataspace.copernicus.eu/) account

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/iran-fire-detection.git
cd iran-fire-detection

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 3. Initialize Database

Run the schema against your PostgreSQL/Supabase instance:

```bash
psql $DATABASE_URL -f schema.sql
```

### 4. Run the Pipeline

```bash
python pipeline.py
```

### 5. Launch the Dashboard

```bash
streamlit run dashboard.py
```

Open `http://localhost:8501` to view the real-time map and warnings.

## ⚙️ Configuration

### Detection Thresholds

These constants in `pipeline.py` control the sensitivity of the detection engine:

| Parameter | Default | Description |
|---|---|---|
| `CONFIDENCE_GATE` | 90 | Minimum VIIRS confidence % to process a hotspot |
| `CLUSTER_DISTANCE_KM` | 2.0 | DBSCAN eps radius for spatial clustering |
| `CLUSTER_MIN_SAMPLES` | 2 | Minimum hotspots to form a cluster core point |
| `FRP_HIGH_ENERGY_MW` | 20.0 | FRP threshold for auto-confirmation |
| `COMPOSITE_CONFIRM` | 65 | Composite score threshold for CONFIRMED status |
| `COMPOSITE_PENDING` | 35 | Composite score threshold for PENDING status |
| `NOTIFICATION_COOLDOWN_H` | 6 | Hours between duplicate alerts for the same fire |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NASA_FIRMS_KEY` | ✅ | NASA FIRMS API map key |
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | Telegram channel or group ID |
| `CDSE_USERNAME` | ✅ | Copernicus CDSE email |
| `CDSE_PASSWORD` | ✅ | Copernicus CDSE password |
| `DATABASE_URL` | ✅ | PostgreSQL/Supabase connection string |

## 📁 Project Structure

```
iran-fire-detection/
├── pipeline.py                  # Main detection pipeline orchestrator
├── dashboard.py                 # Streamlit real-time dashboard
├── schema.sql                   # PostgreSQL/PostGIS database schema
├── requirements.txt             # Python dependencies
├── iran_forest_zone.geojson     # Forest boundary overlay for map
├── .env.example                 # Environment variable template
├── .github/
│   └── workflows/
│       └── fire_detection_cron.yml  # GitHub Actions cron job (30 min)
├── src/
│   ├── config.py                # Configuration & secret management
│   ├── firms_client.py          # NASA FIRMS API client (3-sensor)
│   ├── copernicus_client.py     # Sentinel-2 imagery downloader
│   ├── weather_client.py        # Open-Meteo weather enrichment
│   ├── smoke_detector.py        # CV-based smoke plume analysis
│   ├── spatial_filter.py        # Geospatial forest boundary filter
│   ├── db_client.py             # PostgreSQL/PostGIS database client
│   ├── telegram_notifier.py     # Telegram alert dispatcher
│   └── social_verifier.py       # Citizen crowdsource verification
├── migrations/
│   ├── migration_v2.sql         # Schema migration for v2 columns
│   └── add_detection_columns.py # Python migration script
└── tests/
    └── test_logic.py            # Unit tests
```

## 🚢 Deployment

### GitHub Actions (Recommended)

The included `.github/workflows/fire_detection_cron.yml` runs the pipeline every 30 minutes. Configure these **Repository Secrets** in your GitHub repo settings:

- `NASA_FIRMS_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `CDSE_USERNAME`
- `CDSE_PASSWORD`
- `DATABASE_URL`

### Streamlit Cloud

1. Push to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Set secrets in the Streamlit Cloud dashboard under **Settings → Secrets**

## 📊 Data Sources

| Source | Data | Cost |
|---|---|---|
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | VIIRS active fire hotspots (3 satellites) | Free |
| [Copernicus CDSE](https://dataspace.copernicus.eu/) | Sentinel-2 L2A optical imagery | Free |
| [Open-Meteo](https://open-meteo.com/) | Temperature, humidity, wind, precipitation | Free |

## 🌲 Iran's Forest Regions

The system monitors Iran's three major forest ecosystems:

| Region | Provinces | Forest Type |
|---|---|---|
| **Hyrcanian (Caspian)** | Gilan, Mazandaran, Golestan | Temperate broadleaf, UNESCO World Heritage |
| **Zagros** | Kurdistan, Kermanshah, Lorestan, Ilam, Fars, Kohgiluyeh | Oak-dominant mountain forests |
| **Arasbaran** | East Azerbaijan, Ardabil | Caucasian-mixed mountain forests |

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
