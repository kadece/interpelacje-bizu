"""Klasyfikacja: obszary dzielnicy i tematy (slownik + opcjonalnie LLM Mistral)."""
import json
import os
import unicodedata

import yaml

from . import config, ocr


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def load_taxonomy() -> dict:
    with open(config.TAXONOMY_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_overrides() -> dict:
    if not config.OVERRIDES_PATH.exists():
        return {}
    with open(config.OVERRIDES_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _match_labels(text: str, mapping: dict) -> list:
    normalized = normalize(text)
    found = []
    for label, keywords in (mapping or {}).items():
        if label == "inne" or not keywords:
            continue
        if any(normalize(kw) in normalized for kw in keywords):
            found.append(label)
    return found


def _llm_labels(text: str, allowed: list, kind: str) -> list:
    import requests

    prompt = (
        "Ponizej dokument radnego dzielnicy Ursus (Warszawa). Wybierz najbardziej "
        "pasujace etykiety typu '" + kind + "' WYLICZNIE z listy: " + json.dumps(allowed, ensure_ascii=False) + ". "
        'Odpowiedz TYLKO JSON-em: {"etykiety": ["..."], "pewnosc": 0.0} (pewnosc 0-1). '
        "Jesli zadna nie pasuje, zwroc pusta liste.\n\n" + (text or "")[:6000]
    )
    try:
        response = requests.post(
            config.MISTRAL_API_BASE + "/chat/completions",
            headers={"Authorization": "Bearer " + os.environ["MISTRAL_API_KEY"]},
            json={
                "model": config.SUMMARY_MODEL,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        if response.status_code != 200:
            return []
        parsed = json.loads(response.json()["choices"][0]["message"]["content"])
        confidence = float(parsed.get("pewnosc", 0))
        if confidence < 0.5:
            return []
        return [label for label in parsed.get("etykiety", []) if label in allowed]
    except Exception:  # noqa: BLE001 - bledy klasyfikacji nie blokuja pipeline'u
        return []


def classify(document: dict, taxonomy: dict, *, use_llm: bool = True) -> None:
    text = " ".join(part for part in (document.get("temat"), document.get("tresc")) if part)
    areas = _match_labels(text, taxonomy.get("ulice", {}))
    topics = _match_labels(text, taxonomy.get("tematy", {}))
    if use_llm and ocr.mistral_available():
        if not areas:
            areas = _llm_labels(text, list(taxonomy.get("obszary", [])), "obszar")
        if not topics:
            topics = _llm_labels(text, [t for t in (taxonomy.get("tematy") or {}).keys()], "temat")
    document["obszary"] = sorted(set(areas))[:3]
    topics = sorted(set(topics))[:4]
    document["tematy"] = topics if topics else (["inne"] if document.get("temat") else [])


def apply_overrides(documents: list, overrides: dict) -> None:
    for document in documents:
        rule = (overrides or {}).get(document["id"])
        if not isinstance(rule, dict):
            continue
        if rule.get("obszary") is not None:
            document["obszary"] = rule["obszary"]
        if rule.get("tematy") is not None:
            document["tematy"] = rule["tematy"]
        for field in ("podsumowanie_pismo", "podsumowanie_odpowiedz"):
            if rule.get(field):
                document[field] = rule[field]
                document["podsumowanie_auto"] = False
