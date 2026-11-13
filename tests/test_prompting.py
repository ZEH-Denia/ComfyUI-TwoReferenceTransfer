import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("transfer_prompting", Path(__file__).parents[1] / "prompting.py")
prompting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompting)


class PromptProtocolTests(unittest.TestCase):
    def setUp(self):
        self.analysis = dict.fromkeys(prompting.FIELDS, "visible detail")
        self.analysis.update(identity="long silver hair and blue eyes", pose="Right hand raised; left hand not visible", clothing="Red jacket over a white T-shirt", style="Photograph")

    def test_identity_fields_are_not_transferred(self):
        data = {**self.analysis, "second_person_identity": "second person's face and dark hair"}
        parsed = prompting.parse_analysis("Here is the result:\n```json\n" + json.dumps(data) + "\n```")
        result = prompting.compose_prompt(parsed)
        self.assertNotIn(data["second_person_identity"], result)
        self.assertIn(self.analysis["identity"], result)
        self.assertIn(self.analysis["pose"], result)
        self.assertIn(self.analysis["clothing"], result)

    def test_style_choice_does_not_drop_scene_or_clothes(self):
        for preserve in (True, False):
            result = prompting.compose_prompt(self.analysis, preserve, "Use a wider framing")
            self.assertIn("Red jacket", result)
            self.assertIn("Use a wider framing", result)
            self.assertEqual("Style from Image 2: Photograph" in result, not preserve)

    def test_unavailable_vision_is_not_treated_as_a_caption(self):
        for response in ["I cannot view this image.", '{"error":"vision unavailable"}']:
            with self.assertRaises(ValueError):
                prompting.parse_analysis(response)

    def test_incomplete_response_fails_with_clear_protocol_error(self):
        data = dict(self.analysis)
        del data["expression"]
        with self.assertRaisesRegex(ValueError, "expression"):
            prompting.parse_analysis(json.dumps(data))

    def test_nested_model_details_are_preserved(self):
        data = {**self.analysis, "identity": {"hair": "long silver", "eyes": "blue"}, "clothing": ["red jacket", "white t-shirt"]}
        parsed = prompting.parse_analysis(json.dumps(data))
        self.assertIn("long silver", parsed["identity"])
        self.assertIn("white t-shirt", parsed["clothing"])


if __name__ == "__main__":
    unittest.main()
