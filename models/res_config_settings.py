from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    plate_recognizer_api_token = fields.Char(
        string="Plate Recognizer API Token",
        config_parameter="fleet_plate_extractor.plate_recognizer_api_token",
    )
