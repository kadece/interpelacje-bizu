"""OCR skanow PDF: Mistral OCR (gdy jest klucz) albo lokalny tesseract + poppler."""
import base64
import os
import re
import shutil
import subprocess
import tempfile

from . import config, http


def mistral_available() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY", "").strip())


def _ocr_mistral(pdf_url: str) -> str:
    import requests

    payload = http.get_bytes(pdf_url)
    data_uri = "data:application/pdf;base64," + base64.b64encode(payload).decode("ascii")
    response = requests.post(
        config.MISTRAL_API_BASE + "/ocr",
        headers={"Authorization": "Bearer " + os.environ["MISTRAL_API_KEY"]},
        json={
            "model": config.OCR_MODEL,
            "document": {"type": "document_url", "document_url": data_uri},
        },
        timeout=300,
    )
    if response.status_code != 200:
        raise RuntimeError("Mistral OCR HTTP %d: %s" % (response.status_code, response.text[:200]))
    pages = response.json().get("pages", [])
    return "\n\n".join(page.get("markdown", "") for page in pages).strip()


def _ocr_tesseract(pdf_url: str) -> str:
    if shutil.which("tesseract") is None or shutil.which("pdftoppm") is None:
        raise RuntimeError("Brak tesseract/pdftoppm w systemie; nie mozna przetworzyc skanu")
    payload = http.get_bytes(pdf_url)
    texts = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "scan.pdf")
        with open(pdf_path, "wb") as handle:
            handle.write(payload)
        subprocess.run(["pdftoppm", "-r", "250", "-png", pdf_path, os.path.join(tmp, "strona")],
                       check=True)
        for name in sorted(os.listdir(tmp)):
            if not (name.startswith("strona") and name.endswith(".png")):
                continue
            result = subprocess.run(
                ["tesseract", os.path.join(tmp, name), "stdout", "-l", "pol"],
                capture_output=True, text=True, check=True,
            )
            texts.append(result.stdout)
    return "\n\n".join(texts).strip()


def ocr_quality(text: str) -> float:
    """Prosty wskaznik jakosci OCR: odsetek slow zlozonych z liter."""
    if not text:
        return 0.0
    words = re.findall(r"\S+", text)
    if not words:
        return 0.0
    good = 0
    for word in words:
        stripped = re.sub(r"[^\w]", "", word, flags=re.UNICODE)
        if len(stripped) >= 2 and sum(ch.isalpha() for ch in stripped) / len(stripped) >= 0.6:
            good += 1
    return round(good / len(words), 2)


def ocr_pdf(pdf_url: str) -> tuple:
    """Zwraca (tekst, silnik, jakosc). Najpierw Mistral, przy braku/awarii tesseract."""
    if mistral_available():
        try:
            text = _ocr_mistral(pdf_url)
            if text:
                return text, "mistral-ocr", ocr_quality(text)
        except Exception as error:  # noqa: BLE001 - stiff fallback na tesseract
            print("  ! Mistral OCR nie powiodl sie (%s); probuje tesseract" % error)
    text = _ocr_tesseract(pdf_url)
    return text, "tesseract", ocr_quality(text)
