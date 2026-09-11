import unittest
from unittest.mock import patch

from src.keyword_generator import (
    generate_keywords,
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


if __name__ == "__main__":
    unittest.main()
