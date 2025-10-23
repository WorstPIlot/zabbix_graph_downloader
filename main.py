"""
Zabbix Graph Image Downloader

This script downloads graph images from Zabbix for specified hosts and time ranges
using multithreading for improved performance.
"""

import requests
import json
import datetime
import os
from threading import Thread
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
from urllib.parse import quote

# Configuration - should be moved to environment variables or config file
ZABBIX_API_URL: str = ""
ZABBIX_API_TOKEN: str = ""
ZABBIX_HOST: str = ZABBIX_API_URL.split('/')[2] if ZABBIX_API_URL else ""
WEB_UI_USERNAME: str = ''
WEB_UI_PASSWORD: str = ''

HOST_LIST: List[str] = []  # List of host names to process
TIME_FROM: str = "2024-12-23 00:00:00"
TIME_TILL: str = "2025-12-24 00:00:00"
FORBIDDEN_SYMBOLS: List[str] = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
RESULTING_IMAGE_WIDTH: int = 1920
RESULTING_IMAGE_HEIGHT: int = 200
DOWNLOAD_RETRY_COUNT: int = 500

# Parse time ranges
start_time: datetime.datetime = datetime.datetime.strptime(TIME_FROM, "%Y-%m-%d %H:%M:%S")
end_time: datetime.datetime = datetime.datetime.strptime(TIME_TILL, "%Y-%m-%d %H:%M:%S")


def get_host_id(host_name: str) -> List[Dict[str, str]]:
    """
    Get host ID from Zabbix API by host name.

    Args:
        host_name: Name of the host to look up

    Returns:
        List of dictionaries containing host information, typically:
        [{'hostid': '12345'}]

    Raises:
        requests.HTTPError: If the API request fails
        json.JSONDecodeError: If the response is not valid JSON
    """
    headers: Dict[str, str] = {'Authorization': f'Bearer {ZABBIX_API_TOKEN}'}
    payload: Dict[str, any] = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid"],
            "filter": {"host": host_name}
        },
        "id": 1
    }

    response: requests.Response = requests.post(ZABBIX_API_URL, json=payload, headers=headers)
    response.raise_for_status()

    response_data: Dict[str, any] = json.loads(response.text)
    return response_data['result']


def get_item_list(host_id: str) -> List[Dict[str, str]]:
    """
    Get list of items for a specific host from Zabbix API.

    Args:
        host_id: Host ID to get items for

    Returns:
        List of dictionaries containing item information:
        [{'itemid': '123', 'hostid': '456', 'name': 'CPU Usage'}, ...]

    Raises:
        requests.HTTPError: If the API request fails
        json.JSONDecodeError: If the response is not valid JSON
    """
    headers: Dict[str, str] = {'Authorization': f'Bearer {ZABBIX_API_TOKEN}'}
    payload: Dict[str, any] = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": ["itemid", "hostid", "name"],
            "hostids": host_id
        },
        "id": 1
    }

    response: requests.Response = requests.post(ZABBIX_API_URL, json=payload, headers=headers)
    response.raise_for_status()

    response_data: Dict[str, any] = json.loads(response.text)
    return response_data['result']


def generate_graph_url(
        zabbix_host: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        item_id: str,
        width: int,
        height: int
) -> str:
    """
    Generate URL for graph image download.

    Args:
        zabbix_host: Zabbix server hostname
        start_time: Start time for graph data
        end_time: End time for graph data
        item_id: Item ID to generate graph for
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Complete URL for graph image with proper URL encoding
    """
    base_url: str = f'https://{zabbix_host}/chart.php'

    params: Dict[str, any] = {
        'from': start_time.strftime("%Y-%m-%d %H:%M:%S"),
        'to': end_time.strftime("%Y-%m-%d %H:%M:%S"),
        'itemids[0]': item_id,
        'type': '0',
        'profileIdx': 'web.item.graph.filter',
        'profileIdx2': item_id,
        'width': width,
        'height': height
    }

    # URL encode parameters
    query_string: str = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])

    return f"{base_url}?{query_string}"


def download_image(
        image_url: str,
        file_path: str,
        cookies: Dict[str, str],
        retry_count: int = DOWNLOAD_RETRY_COUNT
) -> bool:
    """
    Download image from URL with retry logic.

    Args:
        image_url: URL to download image from
        file_path: Local filesystem path to save the image
        cookies: Dictionary containing authentication cookies
        retry_count: Maximum number of retry attempts

    Returns:
        True if download was successful, False otherwise
    """
    for attempt in range(retry_count):
        try:
            response: requests.Response = requests.post(image_url, headers=cookies, timeout=30)

            if response.status_code == 200:
                with open(file_path, 'wb') as image_file:
                    image_file.write(response.content)
                print(f'Successfully saved: {file_path}')
                return True
            else:
                print(f'Got {response.status_code} for {image_url}, '
                      f'retry {attempt + 1}/{retry_count}')

        except Exception as error:
            print(f'Error downloading {image_url}: {error}, '
                  f'retry {attempt + 1}/{retry_count}')

    print(f'Failed to download {image_url} after {retry_count} attempts')
    return False


def get_auth_cookies() -> Dict[str, str]:
    """
    Authenticate with Zabbix web UI and get session cookies.

    Returns:
        Dictionary containing Cookie header for authenticated session

    Raises:
        requests.HTTPError: If authentication fails
    """
    login_url: str = f"https://{ZABBIX_HOST}"
    login_data: Dict[str, str] = {
        'form': '1',
        'form_refresh': '1',
        'name': WEB_UI_USERNAME,
        'password': WEB_UI_PASSWORD,
        'enter': 'Enter'
    }

    session: requests.Session = requests.Session()
    response: requests.Response = session.post(login_url, data=login_data)
    response.raise_for_status()

    # Extract cookies from session and format for header
    cookie_dict: Dict[str, str] = session.cookies.get_dict()
    cookie_header: str = '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])

    return {'Cookie': cookie_header}


def sanitize_filename(filename: str) -> str:
    """
    Remove forbidden characters from filename.

    Args:
        filename: Original filename that may contain invalid characters

    Returns:
        Sanitized filename with forbidden characters removed
    """
    sanitized_name: str = filename
    for symbol in FORBIDDEN_SYMBOLS:
        sanitized_name = sanitized_name.replace(symbol, "")
    return sanitized_name


def create_download_queue(cookies: Dict[str, str]) -> Dict[str, str]:
    """
    Build a queue of URLs and file paths for downloading.

    Args:
        cookies: Authenticated cookies for API access

    Returns:
        Dictionary mapping image URLs to local file paths
    """
    download_queue: Dict[str, str] = {}

    for host_name in HOST_LIST:
        print(f"Processing host: {host_name}")

        try:
            host_info: List[Dict[str, str]] = get_host_id(host_name)
            if not host_info:
                print(f"No host found with name: {host_name}")
                continue

            host_id: str = host_info[0]['hostid']

        except (requests.HTTPError, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Failed to get host ID for {host_name}: {e}")
            continue

        # Create host directory
        host_dir: str = os.path.join(os.getcwd(), host_name)
        os.makedirs(host_dir, exist_ok=True)

        try:
            items: List[Dict[str, str]] = get_item_list(host_id)
        except (requests.HTTPError, json.JSONDecodeError) as e:
            print(f"Failed to get items for host {host_name}: {e}")
            continue

        for item in items:
            item_id: str = item['itemid']
            item_name: str = sanitize_filename(item['name'])

            # Generate filename with timestamp
            time_str: str = f"{start_time:%Y-%m-%d_%H%M%S}_{end_time:%Y-%m-%d_%H%M%S}"
            filename: str = f"{host_name}_{item_name}_{item_id}_{time_str}.png"
            file_path: str = os.path.join(host_dir, filename)

            # Skip if file already exists
            if os.path.exists(file_path):
                print(f'Skipping existing file: {file_path}')
                continue

            # Generate graph URL and add to download queue
            graph_url: str = generate_graph_url(
                ZABBIX_HOST, start_time, end_time, item_id,
                RESULTING_IMAGE_WIDTH, RESULTING_IMAGE_HEIGHT
            )
            download_queue[graph_url] = file_path

    return download_queue


def download_images_multithreaded(
        download_queue: Dict[str, str],
        cookies: Dict[str, str]
) -> None:
    """
    Download all images in the queue using multithreading.

    Args:
        download_queue: Dictionary mapping URLs to file paths
        cookies: Authentication cookies for downloads
    """
    if not download_queue:
        print("No images to download.")
        return

    print(f"Starting download of {len(download_queue)} images...")
    threads: List[Thread] = []

    with tqdm(total=len(download_queue), desc="Downloading images") as progress_bar:
        for url, file_path in download_queue.items():
            thread: Thread = Thread(
                target=download_image,
                args=(url, file_path, cookies),
                kwargs={'retry_count': DOWNLOAD_RETRY_COUNT}
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete and update progress
        for thread in threads:
            thread.join()
            progress_bar.update(1)

    print("All downloads completed!")


def main() -> None:
    """Main execution function."""
    # Authenticate and get cookies
    try:
        cookies: Dict[str, str] = get_auth_cookies()
        print("Successfully authenticated with Zabbix")
    except requests.HTTPError as e:
        print(f"Authentication failed with HTTP error: {e}")
        return
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # Build download queue
    download_queue: Dict[str, str] = create_download_queue(cookies)

    # Download all images
    download_images_multithreaded(download_queue, cookies)


if __name__ == "__main__":
    main()
