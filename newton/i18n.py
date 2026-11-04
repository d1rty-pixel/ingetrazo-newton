"""Extension catalogues follow the host language; en.json is the master catalogue."""
import json
from pathlib import Path
from core.i18n import current_language

ROOT = Path(__file__).with_name("i18n")
_catalogues = {}


def catalogue(language):
    if language not in _catalogues:
        try:
            data = json.loads((ROOT/(language+".json")).read_text(encoding="utf-8"))
            _catalogues[language] = data if isinstance(data,dict) else {}
        except (OSError,ValueError):
            _catalogues[language] = {}
    return _catalogues[language]


def tr(source,**values):
    language = current_language() or "en"
    translated = catalogue(language)
    if not translated and "-" in language:
        translated = catalogue(language.split("-")[0])
    text = translated.get(source) or source
    try:
        return text.format(**values) if values else text
    except (KeyError,ValueError,IndexError):
        return source.format(**values) if values else source
