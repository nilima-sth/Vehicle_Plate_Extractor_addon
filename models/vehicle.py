import base64
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__) #for server-side error logging

PLATE_RECOGNIZER_API_URL = "https://api.platerecognizer.com/v1/plate-reader/"
PLATE_RECOGNIZER_API_TOKEN_PARAM = "fleet_plate_extractor.plate_recognizer_api_token"


class PlateVehicleTag(models.Model): #vehicle records can be labeled with tags through a many-to-many relation.
    _name = "plate.vehicle.tag"
    _description = "Vehicle Tag"

    name = fields.Char(required=True)


class PlateVehicle(models.Model):
    _name = "plate.vehicle"
    _description = "Vehicle"
    _rec_name = "license_plate"

    model_name = fields.Char(string="Model", required=True)
    license_plate = fields.Char(string="License Plate")
    plate_image = fields.Image(
        string="Upload Plate Image",
        max_width=1920,
        max_height=1920,
    )
    tag_ids = fields.Many2many("plate.vehicle.tag", string="Tags")

    def _extract_plate_from_image(self, raise_on_error=True):
        self.ensure_one() #ensuring at the method only runs one at a time

        if not self.plate_image:
            if raise_on_error:
                raise UserError(_("Please upload an image first."))
            return False

        api_token = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(PLATE_RECOGNIZER_API_TOKEN_PARAM)
        )
        if not api_token:
            if raise_on_error:
                raise UserError(
                    _("Please configure the Plate Recognizer API token in Settings.")
                )
            return False

        try:
            image_data = base64.b64decode(self.plate_image)
            headers = {"Authorization": f"Token {api_token}"} #HTTP request header creation
            files = {"upload": ("plate_image.jpg", image_data, "image/jpeg")}
            response = requests.post(
                PLATE_RECOGNIZER_API_URL,
                headers=headers,
                files=files,
                timeout=20,
            )
            response.raise_for_status() #so HTTP errors become exceptions
            payload = response.json() #parses the response
        except requests.RequestException as exc:
            _logger.exception("Plate extraction request failed for record %s", self.id)
            if raise_on_error:
                raise UserError(_("Could not reach plate API. Please try again.")) from exc
            return False
        except ValueError as exc:
            _logger.exception("Invalid JSON response for record %s", self.id)
            if raise_on_error:
                raise UserError(_("Plate API returned invalid data.")) from exc
            return False

        results = payload.get("results", [])
        if not results:
            if raise_on_error:
                raise UserError(_("No plate found. Try a clearer image."))
            return False

        extracted_plate = (results[0].get("plate") or "").upper().strip()
        if not extracted_plate:
            if raise_on_error:
                raise UserError(_("Plate detected but value was empty."))
            return False
        return extracted_plate

    @api.onchange("plate_image")
    def _onchange_plate_image_auto_extract(self):
        for record in self:
            if record.plate_image:
                extracted_plate = record._extract_plate_from_image(raise_on_error=False)
                if extracted_plate:
                    record.license_plate = extracted_plate

    def action_extract_plate(self):
        for record in self:
            record.license_plate = record._extract_plate_from_image(raise_on_error=True)
        return True

    @api.model
    def action_hide_fleet_menus(self):
        menu_xmlids = [
            "fleet.menu_root",
            "fleet.fleet_vehicles",
            "fleet.fleet_vehicle_menu",
            "fleet.menu_fleet_reporting",
            "fleet.fleet_configuration",
            "fleet.fleet_config_settings_menu",
        ]
        for xmlid in menu_xmlids:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.exists():
                menu.sudo().write({"active": False})
        return True
