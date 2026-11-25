# Interpelacje BiZU

Nieoficjalna, automatycznie aktualizowana strona z **interpelacjami i zapytaniami klubu radnych „Bezpieczny i Zielony Ursus”** (BiZU) w Radzie Dzielnicy Ursus m.st. Warszawy, kadencja **2024–2029**.

Dane pochodzą w całości z publicznego rejestru [BIP m.st. Warszawy](https://bip.warszawa.pl/web/ursus/interpelacje-zapytania-szukaj) — każdy dokument zawiera link do oryginału i oryginalnych PDF-ów. Strona pozwala filtrować dokumenty **po obszarach dzielnicy, tematach, radnych oraz datach**, pokazuje pełną treść pisma (OCR ze skanu), odpowiedź zarządu dzielnicy (jeżeli udzielono) i krótkie podsumowanie wygenerowane automatycznie.

## Jak to działa

```
Wtorkowy harmonogram (komputer użytkownika):
BIP → lista → strony szczegółów (metadane + PDF)
    → OCR skanów (Mistral OCR lub tesseract) → tagowanie → podsumowania
    → strona statyczna w docs/ → git push → GitHub Pages (branch main, /docs)
```

WAF portalu BIP odrzuca żądania z serwerów chmurowych (m.in. GitHub Actions zwraca HTTP 403) — dlatego pobieranie danych odbywa się z komputera użytkownika, a GitHub wyłącznie publikuje gotową stronę statyczną.

- `pipeline/fetch.py` — stronicowanie przez wyszukiwarkę BIP (filtr: klub BiZU + kadencja 2024–2029),
- `pipeline/parse.py` — metadane i linki PDF ze stron szczegółów,
- `pipeline/ocr.py` — OCR: **Mistral OCR** (gdy ustawiony jest klucz `MISTRAL_API_KEY`) albo lokalny **tesseract** (j. polski),
- `pipeline/classify.py` — obszary i tematy: słownik `config/taxonomy.yml` (+ model, gdy jest klucz),
- `pipeline/summarize.py` — krótkie podsumowania pisma i odpowiedzi (wymaga klucza API),
- `pipeline/build.py` — strona statyczna w `docs/` (bez frameworków: Jinja2 + vanilla JS).

Dane trwałe trzymają się w `data/interpelacje.json`, a gotową stronę w `docs/`; plik `secrets.env` (klucz API) jest ignorowany przez gita.

## Konfiguracja jednorazowa

1. **GitHub Pages**: *Settings → Pages → Build and deployment → Source: **Deploy from a branch*** → branch **main**, folder **/docs**.
2. **Git**: przy pierwszym `git push` pojawia się jednorazowe logowanie GitHub w przeglądarce (kredencjał zapisuje się w menedżerze poświadczeń Windows).
3. **Klucz Mistral API** (opcjonalny — bez niego strony dokumentów linkują tylko do PDF-ów, a podsumowania nie powstają): utwórz w katalogu repo plik `secrets.env` z linią `MISTRAL_API_KEY=...`. Klucz wygenerujesz w [console.mistral.ai](https://console.mistral.ai) (*API keys*; wymaga aktywacji płatności pay-as-you-go).
   - orientacyjny koszt: pierwsze zapełnienie ~750 skanów ≈ **5–7 USD**, potem ok. **5 USD rocznie** (OCR 4 USD/1000 stron, podsumowania grosze).

Aktualizacje uruchamia agent (Mistral Vibe) na komputerze użytkownika: **co tydzień we wtorki** (kontrolnie także w środy) oraz na żądanie. Wymaga włączonego Vibe; pominięty tydzień zostanie nadrobiony przy najbliższej sesji. Pipeline jest przyrostowy i można go uruchamiać dowolnie często.

## Uruchomienie lokalne

```bash
pip install -r pipeline/requirements.txt
python -m pipeline.run --max-pages 1 --max-docs 3   # próbka (bez OCR)
python -m pipeline.run                               # pełny update (OCR: Mistral/tesseract)
python -m pipeline.run --build-only                  # tylko przebudowa strony
```

Wynik: `data/interpelacje.json` + strona w `docs/` (otwórz `docs/index.html` przez dowolny serwer statyczny, np. `python -m http.server -d docs`).

## Ręczne korekty

- tagi i podsumowania per dokument: **`overrides.yml`** (nadpisują automat),
- słowniki obszarów i tematów: **`config/taxonomy.yml`**.

## Zastrzeżenia

Serwis nieoficjalny, tworzony automatycznie. Teksty pochodzą z OCR skanów i mogą zawierać błędy; podsumowania generuje model językowy (zawsze oznaczone) — dokument źródłowy (linkowany) jest rozstrzygający. BIP m.st. Warszawy jest źródłem danych, a jego `robots.txt` nie zabrania pobierania; pipeline odpytuje z opóźnieniem 1,5 s między żądaniami.
