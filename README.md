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

## 🚀 Setup Guide

All data sources and services are free. Total cost to run: **$0/month**.

### 1. Fork the Repository

Click **Fork** on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/iran-fire-detection.git
cd iran-fire-detection

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a Telegram Bot Token & Chat ID

1. Open Telegram, search for **@BotFather**, send `/newbot`
2. Choose a name and username for your bot. You'll receive an **HTTP API token** (e.g. `716819396:AAHP0...`). Save it.
3. Create a **Telegram channel** (e.g. `@IranFireAlerts`) and add your bot as an **administrator**.
4. Send a test message to the channel, then visit this URL in your browser:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
5. Look for `"chat":{"id":-100...}` and copy the numeric ID (e.g. `-1003728633967`).

### 3. Create a Supabase Database

1. Sign up at [supabase.com](https://supabase.com) → **New project**
2. Choose a name (e.g. `iran-fire-watch`), generate a **database password**, and pick a region close to Iran (e.g. Frankfurt).
3. Wait for provisioning, then go to **Settings** → **Database** → **Connection string** → **URI** tab.
4. Copy the string and replace `[YOUR-PASSWORD]` with your database password:
   ```
   postgresql://postgres:YOURPASSWORD@db.xxxxxx.supabase.co:5432/postgres
   ```
5. Create the tables by running this command (uses your `.env` from step 5):
   ```bash
   python -c "import psycopg2, os; from dotenv import load_dotenv; load_dotenv(); conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute(open('schema.sql').read()); conn.commit(); print('Tables created')"
   ```
   If the hostname doesn't resolve (common on some networks), use the **Transaction pooler** connection string (port 6543) in your local `.env` instead.

### 4. Get a NASA FIRMS API Key

1. Visit [firms.modaps.eosdis.nasa.gov/api/map_key/](https://firms.modaps.eosdis.nasa.gov/api/map_key/)
2. Enter your name and email. NASA emails you the key instantly.
3. Save the key.

### 5. Get Copernicus CDSE Credentials

1. Sign up at [dataspace.copernicus.eu](https://dataspace.copernicus.eu/)
2. Use your email as the username and the password you set during registration. **Do not check** the "Copernicus Contributing Missions" box — standard Sentinel-2 access is all you need.

### 6. Configure .env

Copy the template and fill in all values:

```bash
cp .env.example .env
```

Your `.env` should look like:

```env
NASA_FIRMS_KEY=your_nasa_firms_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=-1001111111111
CDSE_USERNAME=you@email.com
CDSE_PASSWORD=your_copernicus_password
DATABASE_URL=postgresql://postgres:YOURPASSWORD@db.xxxxxx.supabase.co:5432/postgres
```

### 7. Configure GitHub Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → add all 6 as **New repository secret**:

| Secret | Value |
|---|---|
| `NASA_FIRMS_KEY` | Your NASA FIRMS key |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your channel numeric ID (e.g. `-1003728633967`) |
| `CDSE_USERNAME` | Your Copernicus email |
| `CDSE_PASSWORD` | Your Copernicus password |
| `DATABASE_URL` | The **direct connection** URI (port 5432), not the pooler |

### 8. Enable GitHub Actions

GitHub disables Actions on forked repos by default:

1. Go to your repo → **Actions** tab
2. Click **"Iran Forest Fire Detection Pipeline"**
3. Click the **"Enable workflow"** button
4. Click **"Run workflow"** → **"Run workflow"** to trigger the first run immediately

The pipeline now runs automatically every 30 minutes, 24/7, at zero cost.

### 9. Deploy the Live Dashboard (Optional)

1. Push your repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io), connect your GitHub account
3. Select this repo, set the main file to `dashboard.py`
4. In the Streamlit Cloud dashboard → **Settings** → **Secrets**, paste all 6 key-value pairs from your `.env` (in TOML format, e.g. `NASA_FIRMS_KEY = "your_key"`)
5. Your dashboard will be live at `https://<app-name>.streamlit.app`

### 10. Download the Smoke Detection Model

The pipeline uses a YOLOv8 model to detect smoke plumes in satellite imagery. You have three options:

**Option A — Automatic (zero config, recommended):**  
The pipeline auto-downloads a free forest-fire detection model from Hugging Face on first run. No setup needed — it just works.

**Option B — Download manually:**
```bash
python download_model.py            # downloads the built-in free model (~22 MB)
python download_model.py --list     # list available sources
python download_model.py --url URL  # download from any direct URL
```

**Option C — Train your own:**  
Use the notebook at `notebooks/smoke_detection_training.ipynb` on Kaggle or Google Colab (free GPU). Place the resulting `model.pt` file in the project root.

**Option D — Custom hosted model:**  
Set `SMOKE_MODEL_URL` in `.env` to a direct download URL for your model. The pipeline downloads it on every run where the local file is missing.

> If no model is available, the pipeline falls back to a computer-vision heuristic smoke detector — functional but less accurate.

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
| `SMOKE_MODEL_URL` | — | Direct download URL for a custom smoke detection model (optional) |

## 🔥 Smoke Detection Model

On first run, the pipeline automatically downloads a free [YOLOv8s forest-fire detection model](https://huggingface.co/touati-kamel/yolov8s-forest-fire-detection) from Hugging Face (~22 MB). The fallback chain is:

1. **Local `model.pt`** — highest priority, use your own trained model
2. **`SMOKE_MODEL_URL`** env var — download from any HTTP URL on each run
3. **Built-in Hugging Face model** — automatic, free, zero-config
4. **CV heuristic** — OpenCV-based smoke analysis (always available, less accurate)

You can also run `python download_model.py` to pre-download the model before your first pipeline run.

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
