import logging
import os
import time

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


TRAIFIC_BASE_URL_PARAM = "traific.base_url"
TRAIFIC_API_TOKEN_PARAM = "traific.api_token"


class OcrApiService(models.AbstractModel):
    _name = "fleet_plate_extractor.ocr_api_service"
    _description = "Flask OCR API Service"

    def _get_base_url(self):
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param(TRAIFIC_BASE_URL_PARAM, "") or ""
        ).strip().rstrip("/")
        if not base_url:
            raise UserError(
                _("Please configure OCR Base URL in Settings (traific.base_url).")
            )
        return base_url

    def _get_token(self):
        token = (
            self.env["ir.config_parameter"].sudo().get_param(TRAIFIC_API_TOKEN_PARAM, "") or ""
        ).strip()
        if not token:
            raise UserError(
                _("Please configure OCR API Token in Settings before running OCR.")
            )
        return token

    def get_ocr_url(self):
        return "%s/api/v1/ocr" % self._get_base_url()

    def send_image_file(self, file_path, timeout=60, retries=1):
        endpoint = self.get_ocr_url()
        token = self._get_token()
        headers = {"X-API-Token": token}

        start = time.monotonic()
        last_exc = None
        _logger.info("OCR request start url=%s", endpoint)

        for attempt in range(retries + 1):
            try:
                with open(file_path, "rb") as image_file:
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        files={"file": (os.path.basename(file_path), image_file, "image/jpeg")},
                        timeout=timeout,
                    )
                duration = time.monotonic() - start
                _logger.info(
                    "OCR request end url=%s status=%s duration=%.3fs",
                    endpoint,
                    response.status_code,
                    duration,
                )
                return self._handle_response(response)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                _logger.warning("OCR request transient failure url=%s attempt=%s", endpoint, attempt + 1)
                if attempt >= retries:
                    raise UserError(
                        _("OCR service is unreachable or timed out. Please retry shortly.")
                    ) from exc
            except OSError as exc:
                raise UserError(_("Could not read image file for OCR request.")) from exc

        raise UserError(_("OCR request failed.")) from last_exc

    def _handle_response(self, response):
        if response.status_code == 401:
            raise UserError(_("Invalid OCR API token. Please verify Settings."))
        if response.status_code == 400:
            raise UserError(_("OCR request data is invalid. Please verify the selected image."))
        if response.status_code == 503:
            raise UserError(_("OCR service unavailable (503). Please try again later."))
        if response.status_code >= 500:
            raise UserError(_("OCR service error. Please retry or contact administrator."))
        if response.status_code != 200:
            raise UserError(_("OCR request failed with status %s.") % response.status_code)

        try:
            payload = response.json()
        except ValueError as exc:
            raise UserError(_("OCR API returned invalid JSON response.")) from exc

        plates = payload.get("plates")
        if plates is None or not isinstance(plates, list):
            raise UserError(_("OCR API response missing 'plates' list."))

        return payload
