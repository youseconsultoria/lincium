from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tests.conftest import TESTDATA_DIR
from src.parsers.santander import parse_file

PDF = TESTDATA_DIR / "SANTANDER 01.2026 - MATRIZ.pdf"


@pytest.fixture(scope="module")
def transactions():
    return parse_file(str(PDF), year=2026)


def test_parsed_minimum_count(transactions):
    assert len(transactions) >= 1800


def test_all_dates_in_january_2026(transactions):
    for tx in transactions:
        assert tx.date.year == 2026
        assert tx.date.month == 1, f"Data fora de janeiro: {tx.date} — {tx.raw_description}"


def test_balance_debits_equal_credits(transactions):
    # Saldo abre e fecha em 0,00 → total créditos == total débitos
    credits = sum(tx.amount for tx in transactions if not tx.is_debit)
    debits = sum(tx.amount for tx in transactions if tx.is_debit)
    diff = abs(credits - debits)
    # Tolerância de R$1 para eventuais arredondamentos no parse
    assert diff < Decimal("1.00"), f"Créditos={credits} Débitos={debits} Diff={diff}"


def test_getnet_are_credits(transactions):
    # GETNET aparece como beneficiary de PAGAMENTO CARTAO (recebimento via maquininha)
    getnet = [tx for tx in transactions if tx.beneficiary and "GETNET" in tx.beneficiary]
    assert len(getnet) > 0, "Nenhuma transação GETNET encontrada"
    for tx in getnet:
        assert not tx.is_debit, f"PAGAMENTO CARTAO/GETNET deve ser crédito: {tx}"


def test_boleto_are_debits(transactions):
    boletos = [tx for tx in transactions if "PAGAMENTO DE BOLETO" in tx.raw_description]
    assert len(boletos) > 0, "Nenhum boleto encontrado"
    for tx in boletos:
        assert tx.is_debit, f"Boleto deve ser débito: {tx}"


def test_contamax_resgate_has_saldo_zero(transactions):
    resgates = [tx for tx in transactions if "RESGATE CONTAMAX" in tx.raw_description]
    assert len(resgates) > 0, "Nenhum resgate CONTAMAX encontrado"
    for tx in resgates:
        assert not tx.is_debit, f"RESGATE CONTAMAX deve ser crédito: {tx}"
        assert tx.saldo == Decimal("0.00"), f"Saldo após CONTAMAX deve ser 0: {tx}"


def test_contamax_aplicacao_are_debits(transactions):
    aplicacoes = [tx for tx in transactions if "APLICACAO CONTAMAX" in tx.raw_description]
    assert len(aplicacoes) > 0, "Nenhuma aplicação CONTAMAX encontrada"
    for tx in aplicacoes:
        assert tx.is_debit, f"APLICACAO CONTAMAX deve ser débito: {tx}"


def test_pix_recebido_are_credits(transactions):
    pix_in = [tx for tx in transactions if tx.raw_description.startswith("PIX RECEBIDO")]
    assert len(pix_in) > 0
    for tx in pix_in:
        assert not tx.is_debit, f"PIX RECEBIDO deve ser crédito: {tx}"


def test_pix_enviado_are_debits(transactions):
    pix_out = [tx for tx in transactions if tx.raw_description.startswith("PIX ENVIADO")]
    assert len(pix_out) > 0
    for tx in pix_out:
        assert tx.is_debit, f"PIX ENVIADO deve ser débito: {tx}"


def test_source_field(transactions):
    for tx in transactions:
        assert tx.source == "santander"


def test_no_zero_amounts(transactions):
    for tx in transactions:
        assert tx.amount >= Decimal("0.01"), f"Valor zero inesperado: {tx}"


def test_total_matches_summary(transactions):
    credits = sum(tx.amount for tx in transactions if not tx.is_debit)
    debits = sum(tx.amount for tx in transactions if tx.is_debit)
    # Valores do resumo da página 2 do extrato
    assert credits == Decimal("1336634.15")
    assert debits == Decimal("1336634.15")
