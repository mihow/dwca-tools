#!/usr/bin/env python3
"""
GBIF Darwin Core Archive Downloader

This script requests a download of occurrence data from GBIF for a list of taxon keys.
It requires a GBIF account (register at https://www.gbif.org/).
"""

import requests
import json
import time
import argparse
import getpass
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def create_download_request(
    taxon_keys: List[str], 
    username: str, 
    email: str,
    format: str = "DWCA"
) -> Dict[str, Any]:
    """
    Create a GBIF download request payload for the given taxon keys.
    
    Args:
        taxon_keys: List of GBIF taxon keys
        username: GBIF username
        email: Email for notification
        format: Download format (DWCA, SIMPLE_CSV, SPECIES_LIST)
        
    Returns:
        Dict containing the request payload
    """
    return {
        "creator": username,
        "notificationAddresses": [email],
        "sendNotification": True,
        "format": format,
        "predicate": {
            "type": "in",
            "key": "TAXON_KEY",
            "values": taxon_keys
        }
    }

def request_download(
    taxon_keys: List[str], 
    username: str, 
    password: str, 
    email: str,
    format: str = "DWCA"
) -> Optional[str]:
    """
    Request a download from GBIF for the given taxon keys.
    
    Args:
        taxon_keys: List of GBIF taxon keys
        username: GBIF username
        password: GBIF password
        email: Email for notification
        format: Download format (DWCA, SIMPLE_CSV, SPECIES_LIST)
        
    Returns:
        Download key if successful, None otherwise
    """
    url = "https://api.gbif.org/v1/occurrence/download/request"
    headers = {"Content-Type": "application/json"}
    payload = create_download_request(taxon_keys, username, email, format)
    
    logger.info(f"Requesting download for {len(taxon_keys)} taxon keys in {format} format")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            auth=(username, password)
        )
        
        response.raise_for_status()
        download_key = response.text.strip('"')
        logger.info(f"Download request successful. Download key: {download_key}")
        return download_key
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting download: {e}")
        return None

def check_download_status(download_key: str) -> Dict[str, Any]:
    """
    Check the status of a GBIF download.
    
    Args:
        download_key: The download key to check
        
    Returns:
        Download status information
    """
    url = f"https://api.gbif.org/v1/occurrence/download/{download_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking download status: {e}")
        return {}

def download_file(download_key: str, output_file: Optional[str] = None) -> bool:
    """
    Download the Darwin Core Archive file.
    
    Args:
        download_key: Download key
        output_file: Path to save the file (default: download_key.zip)
        
    Returns:
        True if successful, False otherwise
    """
    if output_file is None:
        output_file = f"{download_key}.zip"
    
    url = f"https://api.gbif.org/v1/occurrence/download/request/{download_key}.zip"
    
    logger.info(f"Downloading file to {output_file}")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress reporting
        file_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        # Create parent directories if they don't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                # Simple progress indicator
                if file_size > 0:
                    percent = min(100, downloaded * 100 // file_size)
                    sys.stdout.write(f"\rDownloading: {percent}% complete")
                    sys.stdout.flush()
        
        if file_size > 0:
            sys.stdout.write("\n")  # New line after progress
        
        logger.info(f"Download complete: {output_file}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        return False
    except IOError as e:
        logger.error(f"Error saving file: {e}")
        return False

def parse_taxon_keys(input_value: str) -> List[str]:
    """
    Parse taxon keys from a string or file.
    
    Args:
        input_value: Comma-separated list or file path
        
    Returns:
        List of taxon keys
    """
    try:
        # Check if input is a file
        path = Path(input_value)
        if path.is_file():
            with open(path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        else:
            # Treat input as a comma-separated list
            return [key.strip() for key in input_value.split(",") if key.strip()]
    except Exception as e:
        logger.error(f"Error parsing taxon keys: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Download a Darwin Core Archive from GBIF for a list of taxon keys")
    parser.add_argument("--taxon-keys", required=True, 
                        help="Comma-separated list of taxon keys or path to a file with one taxon key per line")
    parser.add_argument("--username", required=True, help="GBIF username")
    parser.add_argument("--email", required=True, help="Email for download notification")
    parser.add_argument("--format", choices=["DWCA", "SIMPLE_CSV", "SPECIES_LIST"], 
                        default="DWCA", help="Download format (default: DWCA)")
    parser.add_argument("--output", help="Output file path (default: download_key.zip)")
    parser.add_argument("--poll-interval", type=int, default=60, 
                        help="Polling interval in seconds (default: 60)")
    parser.add_argument("--max-polls", type=int, default=60, 
                        help="Maximum number of status checks (default: 60)")
    parser.add_argument("--no-wait", action="store_true", 
                        help="Don't wait for the download to complete")
    args = parser.parse_args()
    
    # Get taxon keys
    taxon_keys = parse_taxon_keys(args.taxon_keys)
    
    if not taxon_keys:
        logger.error("No taxon keys provided")
        return
    
    logger.info(f"Processing {len(taxon_keys)} taxon keys")
    
    # Get password
    password = getpass.getpass(f"Password for GBIF user {args.username}: ")
    
    # Request download
    download_key = request_download(
        taxon_keys, 
        args.username, 
        password, 
        args.email,
        args.format
    )
    
    if not download_key:
        return
    
    # Exit if no-wait is specified
    if args.no_wait:
        logger.info(f"Download request submitted. You will receive an email at {args.email} when it's ready.")
        logger.info(f"Download key: {download_key}")
        logger.info(f"You can check the status at https://api.gbif.org/v1/occurrence/download/{download_key}")
        logger.info(f"Download link (when ready): https://api.gbif.org/v1/occurrence/download/request/{download_key}.zip")
        return
    
    # Poll for status
    logger.info(f"Polling for download status every {args.poll_interval} seconds (max {args.max_polls} polls)")
    for i in range(args.max_polls):
        status_info = check_download_status(download_key)
        status = status_info.get("status")
        
        if not status:
            logger.error("Failed to get download status")
            break
        
        logger.info(f"Download status: {status}")
        
        if status == "SUCCEEDED":
            logger.info("Download is ready!")
            # Get DOI if available
            doi = status_info.get("doi")
            if doi:
                logger.info(f"DOI: {doi}")
            
            download_file(download_key, args.output)
            break
        elif status in ["KILLED", "CANCELLED", "FAILED"]:
            logger.error("Download failed")
            error = status_info.get("eraseReason")
            if error:
                logger.error(f"Reason: {error}")
            break
        
        if i < args.max_polls - 1:
            logger.info(f"Waiting {args.poll_interval} seconds before next check...")
            time.sleep(args.poll_interval)
    else:
        logger.warning("Maximum number of status checks reached. The download may still be processing.")
        logger.info(f"You can check the status manually at https://api.gbif.org/v1/occurrence/download/{download_key}")
        logger.info(f"Download link (when ready): https://api.gbif.org/v1/occurrence/download/request/{download_key}.zip")

if __name__ == "__main__":
    main()
