# Interpelacje BiZU

Nieoficjalna, automatycznie aktualizowana strona z **interpelacjami i zapytaniami klubu radnych „Bezpieczny i Zielony Ursus”** (BiZU) w Radzie Dzielnicy Ursus m.st. Warszawy, kadencja **2024–2029**.

Dane pochodzą w całości z publicznego rejestru [BIP m.st. Warszawy](https://bip.warszawa.pl/web/ursus/interpelacje-zapytania-szukaj) — każdy dokument zawiera link do oryginału i oryginalnych PDF-ów. Strona pozwala filtrować dokumenty **po obszarach dzielnicy, tematach, radnych oraz datach**, pokazuje pełną treść pisma (OCR ze skanu), odpowiedź zarządu dzielnicy (jeżeli udzielono) i krótkie podsumowanie wygenerowane automatycznie.

## Jak to działa

```
BIP (wtorkowy cron) → pobranie listy → strony szczegółów (metadane + PDF)
    → OCR skanów → tagowanie obszarów/tematów → podsumowania → strona (site/) → GitHub Pages
```

- `pipeline/fetch.py` — stronicowanie przez wyszukiwarkę BIP (filtr: klub BiZU + kadencja 2024–2029),
- `pipeline/parse.py` — metadane i linki PDF ze stron szczegółów,
- `pipeline/ocr.py` — OCR: **Mistral OCR** (gdy ustawiony jest klucz `MISTRAL_API_KEY`) albo lokalny **tesseract** (j. polski),
- `pipeline/classify.py` — obszary i tematy: słownik `config/taxonomy.yml` (+ model, gdy jest klucz),
- `pipeline/summarize.py` — krótkie podsumowania pisma i odpowiedzi (wymaga klucza API),
- `pipeline/build.py` — strona statyczna w `site/` (bez frameworków: Jinja2 + vanilla JS).

Dane trwałe trzymają się w `data/interpelacje.json` — przy każdym przebiegu aktualizowane są tylko nowe dokumenty i odpowiedzi.

## Konfiguracja jednorazowa

1. **GitHub Pages** (właściciel repo): *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
2. **Klucz Mistral API** (opcjonalny — bez niego OCR robi tesseract, a podsumowania nie są generowane):
   - wygeneruj klucz w [console.mistral.ai](https://console.mistral.ai) (*API keys*, wymaga aktywacji płatności pay-as-you-go),
   - dodaj go w *Settings → Secrets and variables → Actions → New repository secret*: nazwa **`MISTRAL_API_KEY`**.
   - orientacyjny koszt: backfill ~750 skanów ≈ **5–7 USD**, potem ok. **5 USD rocznie** (OCR 4 USD/1000 stron, podsumowania grosze).

Workflow (`.github/workflows/update.yml`) uruchamia się: **we wtorki ok. 5:00–6:00 czasu polskiego** (cron UTC), po każdej zmianie kodu oraz ręcznie (*Actions → „Aktualizacja danych i strona” → Run workflow*, opcjonalnie z pełnym rescanem). Pierwszy przebieg pobiera wszystkie dokumenty od początku kadencji (maj 2024) i może potrwać ok. 1–2 h (OCR). Błędy tworzą zgłoszenie (issue) w repo.

## Uruchomienie lokalne

```bash
pip install -r pipeline/requirements.txt
python -m pipeline.run --max-pages 1 --max-docs 3   # próbka bez OCR domu (bez tesseract)
python -m pipeline.run                               # pełny update (OCR wymaga tesseract + poppler)
python -m pipeline.run --build-only                  # tylko przebudowa strony
```

Wynik: `data/interpelacje.json` + strona w `site/` (otwórz `site/index.html` przez dowolny serwer statyczny, np. `python -m http.server -d site`).

## Ręczne korekty

- tagi i podsumowania per dokument: **`overrides.yml`** (nadpisują automat),
- słowniki obszarów i tematów: **`config/taxonomy.yml`**.

## Zastrzeżenia

Serwis nieoficjalny, tworzony automatycznie. Teksty pochodzą z OCR skanów i mogą zawierać błędy; podsumowania generuje model językowy (zawsze oznaczone) — dokument źródłowy (linkowany) jest rozstrzygający. BIP m.st. Warszawy jest źródłem danych, a jego `robots.txt` nie zabrania pobierania; pipeline odpytuje z opóźnieniem 0,5 s między żądaniami.
