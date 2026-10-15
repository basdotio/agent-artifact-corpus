import unittest

from server_core import TOOLS, build_request


class Seedance25CatalogTests(unittest.TestCase):
    def test_catalog_is_focused(self):
        names = {tool["name"] for tool in TOOLS}
        self.assertEqual(
            names,
            {
                "seedance_25_text_to_video",
                "seedance_25_image_to_video",
                "seedance_25_first_last_frame",
                "seedance_25_omni_reference",
                "muapi_predict_result",
                "muapi_account_balance",
            },
        )

    def test_low_resolution_selects_allowlisted_endpoint(self):
        endpoint, payload = build_request(
            "seedance_25_text_to_video",
            {"prompt": "A paper boat on a stream", "resolution": "480p", "seed": 42},
        )
        self.assertEqual(endpoint, "seedance-2.5-text-to-video-480p")
        self.assertNotIn("resolution", payload)
        self.assertEqual(payload["seed"], 42)

    def test_first_last_frame_requires_two_images(self):
        with self.assertRaises(ValueError):
            build_request(
                "seedance_25_first_last_frame",
                {"prompt": "Transition", "images_list": ["https://example.com/first.jpg"]},
            )


if __name__ == "__main__":
    unittest.main()
