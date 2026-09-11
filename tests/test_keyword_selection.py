import unittest
from unittest.mock import Mock, patch

from src.keyword_generator import (
    generate_keywords,
    is_contextually_relevant_keyword,
    is_generic_keyword,
    select_analysis_keywords,
)


class KeywordSelectionTests(unittest.TestCase):
    def test_caps_at_three_and_keeps_title_first(self):
        keywords = select_analysis_keywords(
            "farmear aura",
            extra=["aura farming"],
            related_terms=["farmear aura qué es", "qué significa aura", "farmear aura batalla"],
        )
        self.assertEqual(len(keywords), 3)
        self.assertEqual(keywords[0], "farmear aura")

    def test_manual_keywords_outrank_related(self):
        keywords = select_analysis_keywords(
            "lujo silencioso",
            extra=["quiet luxury"],
            related_terms=["ropa quiet luxury", "old money"],
        )
        self.assertEqual(keywords[0], "lujo silencioso")
        self.assertEqual(keywords[1], "quiet luxury")
        self.assertEqual(keywords[2], "ropa quiet luxury")

    def test_manual_keywords_fill_all_slots_when_provided(self):
        keywords = select_analysis_keywords(
            "farmear aura",
            extra=["aura points", "farming aura"],
            related_terms=["tik tok aura", "qué es aura", "aura meme"],
        )
        self.assertEqual(len(keywords), 3)
        self.assertEqual(keywords, ["farmear aura", "aura points", "farming aura"])

    def test_deduplication_case_and_whitespace(self):
        keywords = select_analysis_keywords(
            "Farmear Aura",
            extra=["farmear  aura", "FARMEAR AURA", "aura points"],
            related_terms=["farmear aura", "Aura Points", "meme aura"],
        )
        self.assertEqual(len(keywords), 3)
        self.assertEqual(keywords[0], "Farmear Aura")
        self.assertEqual(keywords[1], "aura points")
        self.assertEqual(keywords[2], "meme aura")

    def test_drops_generic_tokens(self):
        keywords = select_analysis_keywords(
            "farmear aura",
            description="Tendencia viral en redes sobre acumular estética",
            related_terms=["viral", "sobre", "farmear aura qué es"],
        )
        lowered = [item.lower() for item in keywords]
        self.assertNotIn("viral", lowered)
        self.assertNotIn("sobre", lowered)
        self.assertIn("farmear aura qué es", lowered)

    def test_empty_related_still_returns_title_and_description_terms(self):
        keywords = select_analysis_keywords(
            "slow travel",
            description="Turismo consciente y viajes de larga estancia",
            related_terms=[],
        )
        self.assertGreaterEqual(len(keywords), 1)
        self.assertEqual(keywords[0], "slow travel")
        self.assertLessEqual(len(keywords), 3)

    def test_generic_detector(self):
        self.assertTrue(is_generic_keyword("viral"))
        self.assertTrue(is_generic_keyword("sobre"))
        self.assertFalse(is_generic_keyword("farmear aura qué es"))

    def test_rejects_single_word_that_loses_trend_context(self):
        keywords = select_analysis_keywords(
            "muerte Jorge Messi",
            ranked_candidates=[
                "muerte Jorge Messi",
                "fallecimiento Jorge Messi",
                "muerte",
            ],
        )
        self.assertEqual(
            keywords,
            ["muerte Jorge Messi", "fallecimiento Jorge Messi"],
        )
        self.assertFalse(
            is_contextually_relevant_keyword("muerte", "muerte Jorge Messi")
        )

    def test_gemini_rejection_is_not_refilled_from_raw_related_queries(self):
        response = type(
            "Response",
            (),
            {
                "text": (
                    '{"keywords":["muerte Jorge Messi","fallecimiento Jorge Messi"],'
                    '"reasoning":"Se descartó muerte porque es demasiado amplia."}'
                )
            },
        )()
        model = Mock()
        model.generate_content.return_value = response

        with (
            patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
            patch("src.keyword_generator._get_model", return_value=model),
        ):
            keywords, reasoning = generate_keywords(
                title="muerte Jorge Messi",
                description="Noticias sobre el fallecimiento del padre de Lionel Messi",
                related_terms=["muerte", "últimas muertes", "Jorge Messi"],
            )

        self.assertEqual(
            keywords,
            ["muerte Jorge Messi", "fallecimiento Jorge Messi"],
        )
        self.assertNotIn("muerte", keywords[1:])
        self.assertIn("descartó muerte", reasoning)

    def test_generate_keywords_fallback_flow(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
            keywords, reasoning = generate_keywords(
                title="social search",
                description="Búsquedas directas en TikTok e Instagram",
                geo="ES",
                extra=["tiktok seo"],
                related_terms=["busquedas en tiktok", "social seo"],
            )
            self.assertEqual(len(keywords), 3)
            self.assertEqual(keywords[0], "social search")
            self.assertEqual(keywords[1], "tiktok seo")
            self.assertIn("Keywords derivadas del título", reasoning)

    def test_missing_api_key_is_reported_in_reasoning(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
            _, reasoning = generate_keywords(
                title="social search",
                description="Búsquedas directas en TikTok e Instagram",
            )

        self.assertIn("Selección sin Gemini", reasoning)
        self.assertIn("GOOGLE_API_KEY", reasoning)

    def test_gemini_failure_reports_type_without_leaking_detail(self):
        model = Mock()
        model.generate_content.side_effect = TimeoutError(
            "https://generativelanguage.googleapis.com/?key=super-secret"
        )

        with (
            patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}),
            patch("src.keyword_generator._get_model", return_value=model),
        ):
            keywords, reasoning = generate_keywords(
                title="social search",
                description="Búsquedas directas en TikTok e Instagram",
                related_terms=["busquedas en tiktok"],
            )

        self.assertEqual(keywords[0], "social search")
        self.assertIn("Gemini no respondió (TimeoutError)", reasoning)
        self.assertNotIn("super-secret", reasoning)


if __name__ == "__main__":
    unittest.main()
