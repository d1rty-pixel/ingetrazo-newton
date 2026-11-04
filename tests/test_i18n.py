import ast
import json
import runpy
import string
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]/"newton"
CATALOGUES = PACKAGE/"i18n"
TRANSLATIONS = sorted(path.stem for path in CATALOGUES.glob("*.json") if path.stem!="en")


def catalogue(language):
    return json.loads((CATALOGUES/(language+".json")).read_text(encoding="utf-8"))


def trees():
    return [ast.parse(path.read_text(encoding="utf-8")) for path in sorted(PACKAGE.glob("*.py"))]


def fields(text):
    return sorted(name for _,name,_,_ in string.Formatter().parse(text) if name is not None)


def test_master_maps_each_english_source_to_itself():
    master = catalogue("en")
    assert master and [key for key,value in master.items() if key!=value]==[]


def test_master_contains_every_static_source():
    sources = {node.args[0].value for tree in trees() for node in ast.walk(tree)
               if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="tr"
               and node.args and isinstance(node.args[0],ast.Constant)}
    # Help texts are passed to tr() by name, so their literals are not tr() arguments.
    sources |= {value for key,value in runpy.run_path(str(PACKAGE/"help_texts.py")).items() if key.isupper() and isinstance(value,str)}
    assert sorted(sources-set(catalogue("en")))==[]


def test_master_has_no_stale_sources():
    # Worker messages and list labels reach tr() as data, so any plain string literal counts as a use.
    literals = set()
    for tree in trees():
        fstring_parts = {id(part) for node in ast.walk(tree) if isinstance(node,ast.JoinedStr) for part in node.values}
        literals |= {node.value for node in ast.walk(tree)
                     if isinstance(node,ast.Constant) and isinstance(node.value,str) and id(node) not in fstring_parts}
    assert sorted(set(catalogue("en"))-literals)==[]


def test_at_least_one_translation_ships():
    assert "de" in TRANSLATIONS


@pytest.mark.parametrize("language",TRANSLATIONS)
def test_translation_has_exactly_the_master_keys(language):
    master,translated = set(catalogue("en")),set(catalogue(language))
    assert {"missing":sorted(master-translated),"extra":sorted(translated-master)}=={"missing":[],"extra":[]}


@pytest.mark.parametrize("language",TRANSLATIONS)
def test_translation_values_are_text_with_the_same_placeholders(language):
    translated = catalogue(language)
    assert [key for key,value in translated.items() if not isinstance(value,str) or not value.strip()]==[]
    assert [key for key,value in translated.items() if fields(key)!=fields(value)]==[]
