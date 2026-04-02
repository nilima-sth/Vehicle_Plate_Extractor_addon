# Vehicle Plate Extractor

This Odoo addon lets users create simple vehicle records, upload a license plate image, and extract the plate number using the Plate Recognizer API.

## Requirements

- Odoo 19
- Python package: `requests`
- A valid Plate Recognizer API token

## Installation

1. Place the module in your custom addons path.
2. Restart the Odoo server.
3. Update the apps list.
4. Install the `Vehicle Plate Extractor` module.

## How To Set Up The API Token

1. Open Odoo.
2. Go to `Settings`.
3. Search for `Vehicle Plate Extractor` or `Plate Recognizer API Token`.
4. In the settings section, enter your Plate Recognizer API token.
5. Click `Save`.

The token is stored in Odoo using the system parameter:

`fleet_plate_extractor.plate_recognizer_api_token`

## How To Use

1. Open `Simple Vehicle`.
2. Go to `Vehicles`.
3. Create a new vehicle record.
4. Enter the vehicle model name.
5. Upload a plate image.
6. The module will try to extract the plate automatically.
7. Save the record.

## Notes

- If no token is configured, the module will ask you to configure it in `Settings`. Under Settings, there is Vehicle Plate Extractor and under the Plate Recognition, put the API token.
- If no plate is detected, try a clearer image.
- The addon uses the external Plate Recognizer service, so internet access from the Odoo server is required.

## Security Recommendation

Do not store real API tokens directly in source code or commit them to Git. If a token was previously exposed, rotate or revoke it before publishing the repository.

## Nepali OCR Setup (Traific Engine)

### 1) On the OCR service host

1. Export the API token used by the OCR Flask service:
	- `export OCR_API_TOKEN="<your-secret-token>"`
2. Start the OCR Flask service.

### 2) In Odoo Settings

Open `Settings` and configure the values under `Vehicle Plate Extractor`:

- `OCR Base URL` (example: `http://127.0.0.1:5000`)
- `Nepali OCR API Token` (must match `OCR_API_TOKEN`)
- `Default Nepali Engine` = `traific`
- Optional timeout with `OCR Timeout (seconds)`

### 3) Validate connectivity

1. Open `Simple Vehicle` -> `Nepali OCR`.
2. Create a record and upload a sample image.
3. Click `Run Nepali OCR`.
4. Verify values are stored in:
	- `nepali_plate_text`
	- `nepali_plate_digits_ascii`
	- `nepali_plate_confidence`

The Nepali OCR endpoint called by Odoo is:

- `POST {OCR_BASE_URL}/api/v1/extract`
- Header: `X-API-Token: <token>`
- Multipart fields: `file`, `engine=traific`, `include_debug=false`
