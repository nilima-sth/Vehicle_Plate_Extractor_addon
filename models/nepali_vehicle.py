import base64
import json
import logging
import os
import tempfile

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PLATE_RECOGNIZER_API_TOKEN_PARAM = "fleet_plate_extractor.plate_recognizer_api_token"
NEPALI_OCR_API_TOKEN_PARAM = "fleet_plate_extractor.nepali_ocr_api_token"
OCR_BASE_URL_PARAM = "fleet_plate_extractor.ocr_base_url"
OCR_TIMEOUT_PARAM = "fleet_plate_extractor.ocr_timeout_seconds"
OCR_DEFAULT_NEPALI_ENGINE_PARAM = "fleet_plate_extractor.default_nepali_engine"
TRAIFIC_BASE_URL_PARAM = "traific.base_url"
TRAIFIC_API_TOKEN_PARAM = "traific.api_token"
DEFAULT_NEPALI_ENGINE = "traific"


class NepaliPlateVehicle(models.Model):
    _name = "plate.vehicle.nepali"
    _description = "Nepali Plate OCR Vehicle"
    _rec_name = "nepali_plate_text"

    name = fields.Char(string="Reference", required=True, default="New")
    image = fields.Image(
        string="Upload Plate Image",
        required=True,
        max_width=1920,
        max_height=1920,
    )
    tag_ids = fields.Many2many("plate.vehicle.tag", string="Tags")
    plate_number = fields.Char(string="Plate Number", readonly=True)
    nepali_plate_text = fields.Char(string="Nepali Plate Text", readonly=True)
    nepali_plate_digits_ascii = fields.Char(string="Digits (ASCII)", readonly=True)
    nepali_plate_confidence = fields.Float(string="Confidence", readonly=True, digits=(16, 4))
    nepali_ocr_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("success", "Success"),
            ("error", "Error"),
        ],
        string="OCR State",
        default="draft",
        readonly=True,
    )
    nepali_ocr_error = fields.Text(string="OCR Error", readonly=True)

    def get_traific_url(self):
        params = self.env["ir.config_parameter"].sudo()
        base_url = (params.get_param(TRAIFIC_BASE_URL_PARAM) or params.get_param(OCR_BASE_URL_PARAM) or "").strip().rstrip("/")
        if not base_url:
            raise UserError(_("Please configure Traific base URL (traific.base_url) in Settings."))
        return "%s/api/v1/ocr" % base_url

    def get_traific_token(self):
        params = self.env["ir.config_parameter"].sudo()
        token = (
            params.get_param(TRAIFIC_API_TOKEN_PARAM)
            or params.get_param(NEPALI_OCR_API_TOKEN_PARAM)
            or params.get_param(PLATE_RECOGNIZER_API_TOKEN_PARAM)
            or ""
        )
        return token.strip()

    def send_to_traific(self, file_path):
        endpoint = self.get_traific_url()
        token = self.get_traific_token()

        headers = {}
        if token:
            headers["X-API-Token"] = token
            headers["Authorization"] = "Bearer %s" % token

        last_conn_error = None
        for attempt in range(2):
            try:
                with open(file_path, "rb") as image_file:
                    files = {
                        "file": (os.path.basename(file_path), image_file, "image/jpeg"),
                    }
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        files=files,
                        timeout=60,
                    )
                break
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_conn_error = exc
                _logger.warning("Traific request failed attempt %s for record %s", attempt + 1, self.id)
                if attempt == 1:
                    _logger.exception("Traific request failed after retry for record %s", self.id)
                    raise UserError(_("Could not reach Traific OCR service (connection/timeout).")) from exc
            except requests.RequestException as exc:
                _logger.exception("Traific request failed for record %s", self.id)
                raise UserError(_("Could not reach Traific OCR service.")) from exc
        else:
            raise UserError(_("Could not reach Traific OCR service.")) from last_conn_error

        if response.status_code == 401:
            raise UserError(_("Traific token is missing or invalid (401 Unauthorized)."))

        if response.status_code != 200:
            detail = response.text
            try:
                error_payload = response.json()
                detail = error_payload.get("error") or detail
            except ValueError:
                pass
            raise UserError(_("Traific OCR service error (%s): %s") % (response.status_code, detail or _("No details")))

        try:
            return response.json()
        except ValueError as exc:
            _logger.exception("Traific OCR JSON parse failed for record %s", self.id)
            raise UserError(_("Traific OCR returned invalid JSON.")) from exc

    def _extract_nepali_from_image(self, raise_on_error=True):
        self.ensure_one()

        if not self.image:
            if raise_on_error:
                raise UserError(_("Please upload an image first."))
            return False

        try:
            image_data = base64.b64decode(self.image)
        except (TypeError, ValueError) as exc:
            if raise_on_error:
                raise UserError(_("Invalid image data.")) from exc
            return False

        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_image:
                temp_image.write(image_data)
                temp_image.flush()
                payload = self.send_to_traific(temp_image.name)
        except UserError:
            if raise_on_error:
                raise
            return False

        plates = payload.get("plates") if isinstance(payload.get("plates"), list) else []
        first_plate = plates[0] if plates else None

        plate_number = ""
        plate_text = ""
        digits_ascii = ""
        avg_conf = 0.0

        if first_plate:
            if isinstance(first_plate, dict):
                plate_number = (
                    first_plate.get("final_text")
                    or first_plate.get("plate")
                    or first_plate.get("text")
                    or ""
                ).strip()
                plate_text = plate_number
                digits_ascii = (first_plate.get("digits_ascii") or "").strip()
                avg_conf = first_plate.get("confidence") or first_plate.get("avg_conf") or 0.0
            else:
                plate_number = str(first_plate).strip()
                plate_text = plate_number

        return {
            "plate_number": plate_number,
            "image": self.image,
            "nepali_plate_text": plate_text,
            "nepali_plate_digits_ascii": digits_ascii,
            "nepali_plate_confidence": float(avg_conf),
            "nepali_ocr_state": "success",
            "nepali_ocr_error": False,
        }

    @api.onchange("image")
    def _onchange_image_auto_extract(self):
        for record in self:
            if record.image:
                extracted = record._extract_nepali_from_image(raise_on_error=False)
                if extracted:
                    # keep selected image visible for user, and assign results
                    record.image = extracted.get("image") or record.image
                    record.plate_number = extracted.get("plate_number")
                    record.nepali_plate_text = extracted.get("nepali_plate_text")
                    record.nepali_plate_digits_ascii = extracted.get("nepali_plate_digits_ascii")
                    record.nepali_plate_confidence = extracted.get("nepali_plate_confidence")
                    record.nepali_ocr_state = extracted.get("nepali_ocr_state")
                    # nepali_ocr_error may be False or a string
                    record.nepali_ocr_error = extracted.get("nepali_ocr_error")

    def action_extract_nepali_plate(self):
        for record in self:
            try:
                extracted = record._extract_nepali_from_image(raise_on_error=True)
                record.write(extracted)
            except UserError as exc:
                # mark record as error and save the OCR error message, then re-raise
                try:
                    record.write({
                        "nepali_ocr_state": "error",
                        "nepali_ocr_error": str(exc),
                    })
                except Exception:
                    pass
                raise
        return True
