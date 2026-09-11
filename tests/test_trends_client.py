import unittest
from unittest.mock import patch

from src.trends_fetcher import (
    PYTRENDS_BACKOFF_FACTOR,
    PYTRENDS_RETRIES,
    PYTRENDS_TIMEOUT,
    _create_pytrend,
    _https_proxies_from_env,
)


class TrendsClientTests(unittest.TestCase):
    def test_client_uses_timeout_retries_and_backoff(self):
        with (
            patch.dict("os.environ", {"PYTRENDS_HTTPS_PROXIES": ""}),
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


if __name__ == "__main__":
    unittest.main()
