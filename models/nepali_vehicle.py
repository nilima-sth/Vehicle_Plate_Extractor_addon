import base64
import json
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
                payload = self.env["fleet_plate_extractor.ocr_api_service"].send_image_file(
                    temp_image.name,
                    timeout=60,
                    retries=1,
                )
        except UserError:
            if raise_on_error:
                raise
            return False

        plates = payload.get("plates") if isinstance(payload.get("plates"), list) else []
        first_plate = plates[0] if plates else None

        plate_number = ""
        plate_text = ""
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
                avg_conf = first_plate.get("confidence") or first_plate.get("avg_conf") or 0.0
            else:
                plate_number = str(first_plate).strip()
                plate_text = plate_number

        return {
            "plate_number": plate_number,
            "image": self.image,
            "nepali_plate_text": plate_text,
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
