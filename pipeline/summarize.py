"""Krotkie podsumowania tresci pisma i odpowiedzi (Mistral API, opcjonalne)."""
import json
import os

import requests

from . import config


def summarize(document: dict) -> None:
    """Uzupelnia document o podsumowanie_pismo / podsumowanie_odpowiedz (auto)."""
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        return
    prompt = (
        "Jestes asystentem biura radnego dzielnicy Ursus (Warszawa). Strecc krótko i konkretnie "
        "(kazde maksymalnie 3 zdania, bez ozdobnikow):\n"
        "1) pole \"pismo\" - o co pyta radny w interpelacji/zapytaniu,\n"
        "2) pole \"odpowiedz\" - co odpowiada zarzad dzielnicy; jesli tresc odpowiedzi jest pusta, "
        "zostaw puste pole.\n"
        'Zwroc TYLKO JSON: {"pismo": "...", "odpowiedz": "..."}\n\n'
        "TEMAT: " + (document.get("temat") or "") + "\n\n"
        "PISMO (OCR):\n" + (document.get("tresc") or "")[:8000] + "\n\n"
        "ODPOWIEDZ (OCR):\n" + (document.get("tresc_odpowiedzi") or "")[:8000]
    )
    try:
        response = requests.post(
            config.MISTRAL_API_BASE + "/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={
                "model": config.SUMMARY_MODEL,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        if response.status_code != 200:
            print("  ! podsumowanie HTTP %d" % response.status_code)
            document["podsumowanie_pismo"] = document.get("podsumowanie_pismo")
            document["podsumowanie_odpowiedz"] = document.get("podsumowanie_odpowiedz") or ""
            return
        parsed = json.loads(response.json()["choices"][0]["message"]["content"])
        if not document.get("podsumowanie_pismo"):
            document["podsumowanie_pismo"] = (parsed.get("pismo") or "").strip() or None
        if not document.get("podsumowanie_odpowiedz"):
            document["podsumowanie_odpowiedz"] = (parsed.get("odpowiedz") or "").strip() or ""
        document["podsumowanie_auto"] = True
    except Exception as error:  # noqa: BLE001 -podsumowanie nie moze zepsuc update'u
        print("  ! podsumowanie nie powiodlo sie: %s" % error)
        if document.get("podsumowanie_odpowiedz") is None:
            document["podsumowanie_odpowiedz"] = ""
