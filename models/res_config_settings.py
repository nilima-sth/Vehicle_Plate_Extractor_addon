from odoo import fields, models


OCR_BASE_URL_PARAM = "fleet_plate_extractor.ocr_base_url"
OCR_TIMEOUT_PARAM = "fleet_plate_extractor.ocr_timeout_seconds"
OCR_DEFAULT_NEPALI_ENGINE_PARAM = "fleet_plate_extractor.default_nepali_engine"
NEPALI_OCR_API_TOKEN_PARAM = "fleet_plate_extractor.nepali_ocr_api_token"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    plate_recognizer_api_token = fields.Char(
        string="Plate Recognizer API Token",
        config_parameter="fleet_plate_extractor.plate_recognizer_api_token",
    )
    nepali_ocr_api_token = fields.Char(
        string="Nepali OCR API Token",
        config_parameter=NEPALI_OCR_API_TOKEN_PARAM,
    )
    ocr_base_url = fields.Char(
        string="OCR Base URL",
        config_parameter=OCR_BASE_URL_PARAM,
        default="http://127.0.0.1:5000",
    )
    ocr_timeout_seconds = fields.Integer(
        string="OCR Timeout (seconds)",
        config_parameter=OCR_TIMEOUT_PARAM,
        default=20,
    )
    nepali_engine = fields.Char(
        string="Default Nepali Engine",
        config_parameter=OCR_DEFAULT_NEPALI_ENGINE_PARAM,
        default="traific",
    )
