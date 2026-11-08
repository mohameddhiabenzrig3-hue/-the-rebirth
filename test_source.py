import ast, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_main_syntax():
    ast.parse((ROOT/'main.py').read_text(encoding='utf-8'))
def test_modules_count():
    data=json.loads((ROOT/'modules.json').read_text(encoding='utf-8'))
    assert len(data)==30
    assert [x['id'] for x in data]==list(range(1,31))
def test_buildozer_has_android():
    spec=(ROOT/'buildozer.spec').read_text()
    assert 'requirements = python3,kivy==2.3.1' in spec
    assert 'package.domain = com.therebirth' in spec
