"""
Simple Odoo-friendly Python client example for TraificNPR Flask microservice.

Usage:
    python examples/odoo_client.py /tmp/plate.jpg

This example demonstrates how an Odoo server (or scheduled action) can call
the local OCR microservice at http://127.0.0.1:5001/api/v1/ocr
"""

import sys
import requests


def send_plate(image_path, base_url="http://127.0.0.1:5001", token=None, timeout=20):
    url = f"{base_url.rstrip('/')}/api/v1/ocr"
    headers = {}
    if token:
        headers["X-API-Token"] = token
    with open(image_path, "rb") as fh:
        files = {"file": (image_path.split("/")[-1], fh, "image/jpeg")}
        try:
            resp = requests.post(url, files=files, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            return {"error": f"request-failed: {e}"}

    if resp.status_code == 200:
        try:
            return resp.json()
        except ValueError:
            return {"error": "invalid-json-response", "status_code": resp.status_code}
    elif resp.status_code == 400:
        return {"error": "bad-request", "status_code": 400, "detail": resp.text}
    elif resp.status_code == 401:
        return {"error": "unauthorized", "status_code": 401, "detail": resp.text}
    else:
        return {"error": "server-error", "status_code": resp.status_code, "detail": resp.text}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/odoo_client.py /path/to/plate.jpg")
        sys.exit(1)
    image = sys.argv[1]
    result = send_plate(image)
    print(result)
