"""Download a fire/smoke detection YOLOv8 model for use with the pipeline.

Usage:
    python download_model.py                               # built-in free Hugging Face model
    python download_model.py --url <HTTPS_URL>             # custom URL (HTTPS only)
    python download_model.py --source hf-forest-fire       # Hugging Face (default)
    python download_model.py --list                        # show available sources
"""

import os
import sys
import argparse
from urllib.parse import urlparse
import requests

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "model.pt")

SOURCES = {
    "hf-forest-fire": {
        "name": "YOLOv8s Forest Fire Detection (Hugging Face)",
        "description": "YOLOv8s fine-tuned on forest fire imagery. ~22 MB. "
                       "Best general-purpose free option for satellite smoke detection.",
        "url": "https://huggingface.co/touati-kamel/yolov8s-forest-fire-detection/resolve/main/model.pt",
        "classes": ["fire", "smoke"],
    },
}


def validate_url(url):
    """Reject non-HTTPS URLs to prevent SSRF and local file disclosure."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are allowed. Got scheme '{parsed.scheme or 'none'}'.")
    if not parsed.netloc:
        raise ValueError("URL must include a hostname.")


def download_file(url, dest, label):
    """Download a file with progress reporting. Writes atomically via temp file."""
    validate_url(url)
    tmp_path = dest + ".download"
    print(f"Downloading {label} ...")
    print(f"  URL: {url}")
    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = (downloaded / total) * 100
                    mb_done = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    print(f"\r  Progress: {pct:.0f}% ({mb_done:.1f} / {mb_total:.1f} MB)", end="")
        os.replace(tmp_path, dest)
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"\r  Done: {size_mb:.1f} MB saved to {dest}")
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        for p in (dest, tmp_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download a fire/smoke detection model for Iran Fire Watch"
    )
    parser.add_argument(
        "--source", "-s",
        choices=list(SOURCES.keys()),
        default="hf-forest-fire",
        help="Which built-in model source to download (default: hf-forest-fire)",
    )
    parser.add_argument(
        "--url", "-u",
        help="Direct download URL for a custom model (overrides --source)",
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available built-in model sources and exit",
    )

    args = parser.parse_args()

    if args.list:
        print("Available built-in model sources:\n")
        for key, info in SOURCES.items():
            print(f"  {key}")
            print(f"    Name:        {info['name']}")
            print(f"    Description: {info['description']}")
            print(f"    Classes:     {', '.join(info['classes'])}")
            print()
        print("Custom model:")
        print("  Use --url to download from any direct URL.")
        print("  Train your own with the notebook at notebooks/smoke_detection_training.ipynb")
        print("  Or search Hugging Face: https://huggingface.co/models?search=yolov8+fire+detection")
        return

    if args.url:
        url = args.url
        label = "custom URL"
    else:
        source = SOURCES[args.source]
        url = source["url"]
        label = source["name"]

    # Prevent path traversal via --output
    output = os.path.realpath(args.output)
    if not output.startswith(os.path.realpath(PROJECT_ROOT) + os.sep):
        print(f"Error: --output must be inside the project directory ({PROJECT_ROOT}).")
        print(f"Got: {args.output}")
        sys.exit(1)

    if os.path.exists(output):
        print(f"Model already exists at {output}")
        print("Remove it first if you want to re-download, or use --output for a different path.")
        return

    success = download_file(url, output, label)
    if success:
        print(f"\nModel ready. The pipeline will use it automatically on the next run.")
    else:
        print(f"\nDownload failed. The pipeline will fall back to CV heuristics.")
        print("You can also:")
        print("  - Place any YOLOv8 .pt file at model.pt in the project root")
        print(f"  - Set SMOKE_MODEL_URL in .env to a direct download URL")
        sys.exit(1)


if __name__ == "__main__":
    main()
