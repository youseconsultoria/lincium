import pytest
from tests.conftest import TESTDATA_DIR, COMPROVANTES_DIR
from src.parsers.detector import detect_parser
from src.parsers.santander import parse_file as parse_santander
from src.parsers.banco_do_brasil import parse_file as parse_banco_do_brasil
from src.parsers.sicoob import parse_file as parse_sicoob
from src.parsers.bradesco_comprovante import parse_file as parse_bradesco_comprovante
from src.parsers.itau_comprovante import parse_file as parse_itau_comprovante


CASES = [
    (TESTDATA_DIR / "SANTANDER 01.2026 - MATRIZ.pdf", parse_santander),
    (TESTDATA_DIR / "BANCO DO BRASIL - 01.2026 .pdf", parse_banco_do_brasil),
    (TESTDATA_DIR / "SICOOB - 01.2026.pdf", parse_sicoob),
    (COMPROVANTES_DIR / "Bradesco_06052026_161939.PDF", parse_bradesco_comprovante),
    (COMPROVANTES_DIR / "Extrato_0126_593771_itau - comprovantes - OK.pdf", parse_itau_comprovante),
]


@pytest.mark.parametrize("pdf_path,expected_parser", CASES)
def test_detects_correct_parser(pdf_path, expected_parser):
    detected = detect_parser(str(pdf_path))
    assert detected == expected_parser, (
        f"{pdf_path.name}: esperado {expected_parser.__module__}, "
        f"detectado {detected.__module__}"
    )
