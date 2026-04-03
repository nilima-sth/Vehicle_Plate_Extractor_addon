import base64
from unittest.mock import Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNepaliOCR(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vehicle_model = self.env["plate.vehicle.nepali"]
        self.params = self.env["ir.config_parameter"].sudo()
        self.params.set_param("traific.api_token", "secret-token")
        self.params.set_param("traific.base_url", "http://127.0.0.1:5001")
        self.params.set_param("fleet_plate_extractor.default_nepali_engine", "traific")
        self.params.set_param("fleet_plate_extractor.ocr_timeout_seconds", "10")

    def _make_vehicle(self):
        return self.vehicle_model.create(
            {
                "name": "NP Test",
                "image": base64.b64encode(b"fake-image-bytes"),
            }
        )

    def test_action_extract_nepali_plate_success(self):
        vehicle = self._make_vehicle()

        mocked_response = Mock()
        mocked_response.status_code = 200
        mocked_response.content = b"ok"
        mocked_response.json.return_value = {
            "plates": [
                {
                    "final_text": "बा १२ च ३४५६",
                    "digits_ascii": "12-3456",
                    "confidence": 0.8732,
                }
            ]
        }

        with patch("odoo.addons.fleet_plate_extractor.models.nepali_vehicle.requests.post", return_value=mocked_response) as mocked_post:
            vehicle.action_extract_nepali_plate()

        mocked_post.assert_called_once()
        post_kwargs = mocked_post.call_args.kwargs
        self.assertEqual(post_kwargs["timeout"], 60)
        self.assertIn("X-API-Token", post_kwargs["headers"])
        self.assertEqual(post_kwargs["headers"]["X-API-Token"], "secret-token")

        self.assertEqual(vehicle.nepali_ocr_state, "success")
        self.assertTrue(vehicle.image)
        self.assertEqual(vehicle.plate_number, "बा १२ च ३४५६")
        self.assertEqual(vehicle.nepali_plate_text, "बा १२ च ३४५६")
        self.assertEqual(vehicle.nepali_plate_digits_ascii, "12-3456")
        self.assertAlmostEqual(vehicle.nepali_plate_confidence, 0.8732, places=4)
        self.assertFalse(vehicle.nepali_ocr_error)


    def test_action_extract_nepali_plate_unauthorized(self):
        vehicle = self._make_vehicle()

        mocked_response = Mock()
        mocked_response.status_code = 401
        mocked_response.content = b"unauthorized"
        mocked_response.text = '{"error": "Unauthorized"}'
        mocked_response.json.return_value = {"error": "Unauthorized"}

        with patch("odoo.addons.fleet_plate_extractor.models.nepali_vehicle.requests.post", return_value=mocked_response):
            with self.assertRaises(UserError):
                vehicle.action_extract_nepali_plate()

        self.assertEqual(vehicle.nepali_ocr_state, "error")
        self.assertIn("401", vehicle.nepali_ocr_error)

    def test_missing_traific_base_url(self):
        vehicle = self._make_vehicle()
        self.params.set_param("traific.base_url", "")

        with self.assertRaises(UserError):
            vehicle.action_extract_nepali_plate()
