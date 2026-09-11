import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.trends_fetcher import (
    PYTRENDS_BACKOFF_FACTOR,
    PYTRENDS_RETRIES,
    PYTRENDS_TIMEOUT,
    _create_pytrend,
    _https_proxies_from_env,
    _requests_args_from_env,
    fetch_interest_over_time,
    fetch_related_queries,
)


class TrendsClientTests(unittest.TestCase):
    def test_client_uses_timeout_retries_and_backoff(self):
        with (
            patch.dict("os.environ", {"PYTRENDS_HTTPS_PROXIES": ""}, clear=True),
            patch("src.trends_fetcher.TrendReq") as trend_req,
        ):
            _create_pytrend()

        trend_req.assert_called_once_with(
            hl="es-ES",
            tz=360,
            timeout=PYTRENDS_TIMEOUT,
            proxies=[],
            retries=PYTRENDS_RETRIES,
            backoff_factor=PYTRENDS_BACKOFF_FACTOR,
            requests_args={},
        )

    def test_reads_comma_separated_https_proxies(self):
        value = "https://proxy-a.example:443, https://user:pass@proxy-b.example:8443"
        with patch.dict("os.environ", {"PYTRENDS_HTTPS_PROXIES": value}):
            proxies = _https_proxies_from_env()

        self.assertEqual(
            proxies,
            [
                "https://proxy-a.example:443",
                "https://user:pass@proxy-b.example:8443",
            ],
        )

    def test_rejects_non_https_proxy(self):
        with patch.dict(
            "os.environ",
            {"PYTRENDS_HTTPS_PROXIES": "http://proxy.example:8080"},
        ):
            with self.assertRaisesRegex(ValueError, "URLs HTTPS con puerto"):
                _https_proxies_from_env()

    def test_passes_custom_ca_bundle_with_tls_verification(self):
        with patch.dict(
            "os.environ",
            {"REQUESTS_CA_BUNDLE": "/path/to/company-ca.pem"},
            clear=True,
        ):
            self.assertEqual(
                _requests_args_from_env(),
                {"verify": "/path/to/company-ca.pem"},
            )

    @patch("src.trends_fetcher._create_pytrend")
    def test_related_queries_uses_modern_payload_and_response(self, create_client):
        client = MagicMock()
        client.related_queries.return_value = {
            "seed-modern-client": {
                "top": pd.DataFrame([{"query": "top term", "value": 100}]),
                "rising": pd.DataFrame([{"query": "rising term", "value": "Breakout"}]),
            }
        }
        create_client.return_value = client

        result = fetch_related_queries(
            "seed-modern-client",
            timeframe="today 3-m",
            max_retries=1,
        )

        client.build_payload.assert_called_once_with(
            ["seed-modern-client"],
            cat=0,
            timeframe="today 3-m",
            geo="ES",
            gprop="",
        )
        client.related_queries.assert_called_once_with()
        self.assertEqual(result["top"][0], {"query": "top term", "value": 100})
        self.assertEqual(
            result["rising"][0],
            {"query": "rising term", "value": "Breakout"},
        )

    @patch("src.trends_fetcher._create_pytrend")
    def test_interest_over_time_keeps_one_consolidated_request(self, create_client):
        client = MagicMock()
        frame = pd.DataFrame(
            {
                "first-modern": [10],
                "second-modern": [20],
                "third-modern": [30],
                "isPartial": [False],
            },
            index=pd.to_datetime(["2026-09-10"]),
        )
        client.interest_over_time.return_value = frame
        create_client.return_value = client
        keywords = ["first-modern", "second-modern", "third-modern"]

        result = fetch_interest_over_time(
            keywords,
            timeframe="today 3-m",
            max_retries=1,
        )

        client.build_payload.assert_called_once_with(
            keywords,
            cat=0,
            timeframe="today 3-m",
            geo="ES",
            gprop="",
        )
        client.interest_over_time.assert_called_once_with()
        self.assertEqual(list(result.columns), keywords)


if __name__ == "__main__":
    unittest.main()
