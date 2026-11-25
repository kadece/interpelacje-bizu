"""Stała konfiguracja pipeline'u (adresy BIP, ID kategorii Liferay, modele Mistral)."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
SITE_DIR = REPO_ROOT / "site"
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"
TAXONOMY_PATH = REPO_ROOT / "config" / "taxonomy.yml"
OVERRIDES_PATH = REPO_ROOT / "overrides.yml"

BIP_BASE = "https://bip.warszawa.pl"
SEARCH_URL = BIP_BASE + "/web/ursus/interpelacje-zapytania-szukaj"
DETAIL_PREFIX = "/web/ursus/-/"

# Kategorie w portalu Liferay (stan na XI 2026)
CLUB_BIZU_ID = 1971629
KADENCJA_ID = 1046979
DISTRICT_URSUS_ID = 46406

HTTP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
REQUEST_DELAY_S = 0.5
REQUEST_TIMEOUT_S = 30
MAX_RETRIES = 4

MISTRAL_API_BASE = "https://api.mistral.ai/v1"
OCR_MODEL = "mistral-ocr-latest"
SUMMARY_MODEL = "mistral-small-latest"
