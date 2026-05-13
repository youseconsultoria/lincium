from datetime import date
from decimal import Decimal

from tests.conftest import TESTDATA_DIR
from src.parsers.banco_do_brasil import parse_file

PDF = TESTDATA_DIR / "BANCO DO BRASIL - 01.2026 .pdf"


def test_parse_single_transaction():
    txs = parse_file(str(PDF))
    # Conta com mínimo movimento: 1 tarifa
    assert len(txs) == 1


def test_tarifa_is_debit():
    txs = parse_file(str(PDF))
    assert txs[0].is_debit is True


def test_tarifa_amount():
    txs = parse_file(str(PDF))
    assert txs[0].amount == Decimal("232.30")


def test_tarifa_date():
    txs = parse_file(str(PDF))
    assert txs[0].date == date(2026, 1, 20)


def test_source():
    txs = parse_file(str(PDF))
    assert txs[0].source == "banco_do_brasil"


def test_description_contains_tarifa():
    txs = parse_file(str(PDF))
    assert "Tarifa" in txs[0].raw_description
