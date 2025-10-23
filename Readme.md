# Zabbix Graph Image Downloader

A Python script for bulk downloading graph images from Zabbix monitoring system with multithreading support.

## Features

- 📊 Bulk download graph images for multiple hosts
- ⚡ Multithreaded downloads for improved performance
- 🎯 Configurable time ranges and image dimensions
- 📁 Automatic organization by hostname
- 🔄 Robust retry mechanism for failed downloads
- ✅ PEP 8 compliant with type hints

## Quick Start

### Prerequisites

- Python 3.7+
- Zabbix API access token
- Web UI credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd zabbix-graph-downloader
```

    Install dependencies:

```bash
pip install requests tqdm
```

### Configuration

Edit the configuration section in zabbix_downloader.py:
```python
ZABBIX_API_URL = "https://your-zabbix-server/api_jsonrpc.php"
ZABBIX_API_TOKEN = "your_api_token_here"
WEB_UI_USERNAME = "your_username"
WEB_UI_PASSWORD = "your_password"
HOST_LIST = ["host1", "host2", "host3"]
```

### Usage

Run the script:
```bash
python zabbix_downloader.py
```
The script will:

1) Authenticate with Zabbix API
2) Fetch all items for specified hosts
3) Generate graph URLs for the configured time range
4) Download images concurrently to host-specific folders

Configuration Options
Setting	Description	Default
1) TIME_FROM / TIME_TILL:	Graph time range = 2025-01-01 to 2025-10-24
2) RESULTING_IMAGE_WIDTH:	Image width in pixels = 1920
3) RESULTING_IMAGE_HEIGHT:	Image height in pixels = 200
4) DOWNLOAD_RETRY_COUNT:	Max retry attempts for failed downloads = 500

Feel free to improve and fork
