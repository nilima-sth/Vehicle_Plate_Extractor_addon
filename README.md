# Vehicle Plate Extractor

Odoo addon to extract license plates from images and perform Nepali OCR via external APIs.

## Overview

- `plate.vehicle`: basic vehicle with image upload + Plate Recognizer API
- `plate.vehicle.nepali`: Nepali plate OCR using external OCR service
- `res.config.settings` parameters configure tokens, endpoints, and timeout
- Hides default fleet menus via `action_hide_fleet_menus`

## Requirements

- Odoo 19
- Python dependency: `requests` (declared in manifest)
- Module dependency: `base`
- Internet access on Odoo server for API calls

## Installation

1. Copy `fleet_plate_extractor` into your custom addons path.
2. Restart the Odoo server.
3. Update apps list.
4. Install `Vehicle Plate Extractor`.

## Configuration

### Plate Recognizer account and API key

1. Visit the Plate Recognizer website:
   - https://platerecognizer.com/
2. Sign up for an account and verify your email.
3. Go to dashboard -> API tokens and create a new token.
4. Copy the token value and configure in Odoo:
   - `fleet_plate_extractor.plate_recognizer_api_token`

### Nepali OCR settings (optional)

In Odoo Settings, search for `Vehicle Plate Extractor` and set:

- Plate Recognizer API token: `fleet_plate_extractor.plate_recognizer_api_token`
- Nepali OCR API token: `fleet_plate_extractor.nepali_ocr_api_token` (optional fallback to Plate Recognizer token)
- OCR Base URL: `fleet_plate_extractor.ocr_base_url` (example: `http://127.0.0.1:5000`)
- Default Nepali Engine: `fleet_plate_extractor.default_nepali_engine` (default: `traific`)
- OCR Timeout: `fleet_plate_extractor.ocr_timeout_seconds` (default: 20)

> Note: Tokens should be stored in Odoo parameters, not in source code or SCM.

## Plate Recognizer (License Plate Extractor) Usage

1. Go to `Simple Vehicle` -> `Vehicles`.
2. Create a `Vehicle` record.
3. Fill `Model`.
4. Upload `Upload Plate Image`.
5. On image upload, `license_plate` is auto-extracted.
6. Optionally run action `Extract Plate` (button in form view) to force extraction.

### Behavior

- Extracted plate is saved to `license_plate`.
- If no plate found or API error occurs, user receives a warning.

## Nepali OCR Usage

1. Go to `Simple Vehicle` -> `Nepali OCR`.
2. Create `Nepali Plate OCR Vehicle` record.
3. Fill `Reference` and upload `Upload Plate Image`.
4. On upload, OCR is attempted automatically (non-blocking).
5. Use `Run Nepali OCR` action if not auto-run.

### Output fields

- `nepali_plate_text`
- `nepali_plate_digits_ascii`
- `nepali_plate_confidence`
- `nepali_ocr_state` (`draft`/`success`/`error`)
- `nepali_ocr_error`

## Nepali OCR Microservice (traific)

This module expects a Nepali OCR microservice with a REST interface that accepts image files and returns JSON with OCR results.

### TraificNPR model source

- Repo: https://github.com/nilima-sth/nepali-ocrs.git
- Module folder: `TraificNPR`
- Startup script included: `TraificNPR/run.sh`

### Recommended local service setup (example)

1. Clone and inspect run script:
   - `git clone https://github.com/nilima-sth/nepali-ocrs.git`
   - `cd nepali-ocrs/TraificNPR`
   - `chmod +x run.sh`
2. Prepare isolated Python environment (venv) on OCR host.
3. Install required packages (Flask + OCR engine wrapper). Example:
   - `pip install flask requests` (plus dependencies from `TraificNPR/pyproject.toml` as needed)
4. Run service:
   - `./run.sh` (or follow local instructions in the repo)
5. Confirm endpoint is reachable:
   - `curl -X POST http://127.0.0.1:5000/api/v1/extract -H "X-API-Token: <token>" -F "file=@plate.jpg" -F "engine=traific" -F "include_debug=false"`

### Odoo parameter mapping

- `fleet_plate_extractor.nepali_ocr_api_token` (or fallback to Plate Recognizer API token)
- `fleet_plate_extractor.ocr_base_url` (e.g., `http://127.0.0.1:5000`)
- `fleet_plate_extractor.default_nepali_engine` (`traific` by default)
- `fleet_plate_extractor.ocr_timeout_seconds` (default 20)

### Expected microservice contract

- Endpoint: `POST {OCR_BASE_URL}/api/v1/extract`
- Header: `X-API-Token: <token>`
- Form data:
  - `file` (image)
  - `engine` (e.g. `traific`)
  - `include_debug` (true/false)

Response expected JSON:

- `status`: `ok` or `error`
- `plate_text`, `digits_ascii`, `avg_conf` on success
- `error` on failure

## API Endpoints

- Plate Recognizer: `https://api.platerecognizer.com/v1/plate-reader/`
- Nepali OCR: `{OCR_BASE_URL}/api/v1/extract`
  - Header: `X-API-Token: <token>`
  - Fields: `file`, `engine=<engine>`, `include_debug=false`

## Development and Testing

- Models:
  - `fleet_plate_extractor/models/vehicle.py`
  - `fleet_plate_extractor/models/nepali_vehicle.py`
  - `fleet_plate_extractor/models/res_config_settings.py`
- Views:
  - `/views/vehicle_views.xml`
  - `/views/nepali_vehicle_views.xml`
  - `/views/res_config_settings_views.xml`
- Test file: `/tests/test_nepali_ocr.py`

## Security

- Do not commit API tokens into repository.
- Remove sensitive default values before sharing.
- Revoke/rotate tokens after exposure.

## Troubleshooting

- Ensure `requests` is installed in Odoo Python environment.
- If extraction fails, verify API token and network connectivity.
- For 401/422 from OCR service, confirm `X-API-Token` and engine settings.
