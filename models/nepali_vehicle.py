import base64
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PLATE_RECOGNIZER_API_TOKEN_PARAM = "fleet_plate_extractor.plate_recognizer_api_token"
NEPALI_OCR_API_TOKEN_PARAM = "fleet_plate_extractor.nepali_ocr_api_token"
OCR_BASE_URL_PARAM = "fleet_plate_extractor.ocr_base_url"
OCR_TIMEOUT_PARAM = "fleet_plate_extractor.ocr_timeout_seconds"
OCR_DEFAULT_NEPALI_ENGINE_PARAM = "fleet_plate_extractor.default_nepali_engine"
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

    def _get_ocr_config(self):
        params = self.env["ir.config_parameter"].sudo()
        token = params.get_param(NEPALI_OCR_API_TOKEN_PARAM) or params.get_param(
            PLATE_RECOGNIZER_API_TOKEN_PARAM
        )
        base_url = (params.get_param(OCR_BASE_URL_PARAM) or "").strip().rstrip("/")
        engine = (params.get_param(OCR_DEFAULT_NEPALI_ENGINE_PARAM) or DEFAULT_NEPALI_ENGINE).strip() or DEFAULT_NEPALI_ENGINE

        timeout_raw = params.get_param(OCR_TIMEOUT_PARAM) or "20"
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError):
            timeout = 20
        timeout = max(timeout, 1)

        if not token:
            raise UserError(_("Please configure the Nepali OCR API token in Settings."))
        if not base_url:
            raise UserError(_("Please configure the OCR Base URL in Settings."))

        return {
            "token": token,
            "base_url": base_url,
            "engine": engine,
            "timeout": timeout,
        }

    def _call_ocr_service(self, image_data, engine, include_debug=False):
        config = self._get_ocr_config()
        endpoint = "%s/api/v1/extract" % config["base_url"]
        headers = {
            "X-API-Token": config["token"],
        }
        files = {
            "file": ("plate_image.jpg", image_data, "image/jpeg"),
        }
        data = {
            "engine": engine,
            "include_debug": "true" if include_debug else "false",
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=config["timeout"],
            )
        except requests.RequestException as exc:
            _logger.exception("Nepali OCR request failed for record %s", self.id)
            raise UserError(_("Could not reach OCR service. Please try again.")) from exc

        payload = {}
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = {}

        if response.status_code in (400, 401, 422, 500):
            error_text = payload.get("error") or response.text or _("OCR service returned an error.")
            raise UserError(_("OCR service error (%s): %s") % (response.status_code, error_text))

        if response.status_code >= 400:
            raise UserError(_("Unexpected OCR service error (%s).") % response.status_code)

        return payload

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
            config = self._get_ocr_config()
            payload = self._call_ocr_service(
                image_data=image_data,
                engine=config["engine"],
                include_debug=False,
            )
            if payload.get("status") != "ok":
                error_text = payload.get("error") or _("OCR service did not return success status.")
                if raise_on_error:
                    raise UserError(error_text)
                return False
        except UserError:
            if raise_on_error:
                raise
            return False

        plate_text = (payload.get("plate_text") or "").strip()
        digits_ascii = (payload.get("digits_ascii") or "").strip()
        avg_conf = payload.get("avg_conf") or 0.0
        return {
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
                    record.update(extracted)

    def action_extract_nepali_plate(self):
        for record in self:
            extracted = record._extract_nepali_from_image(raise_on_error=True)
            record.write(extracted)
        return True
