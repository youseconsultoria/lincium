from datetime import date
from decimal import Decimal

from src.models import Transaction, Comprovante
from src.matching.engine import MatchEngine
from src.matching.rules import EmpresaConfig
from src.matching.plano_de_contas import PlanoDeContas, ContaEntry

CFG = EmpresaConfig.stub()
PLANO = PlanoDeContas.stub()

# Adiciona conta fictícia de fornecedor para testes de comprovante
PLANO.add(ContaEntry("999", "FORNECEDOR TESTE LTDA", "D", cnpj="12345678000195"))

ENGINE = MatchEngine(CFG, PLANO)


def _tx(desc, amount, is_debit=True, dt=None, ben=None):
    return Transaction(
        date=dt or date(2026, 1, 5),
        raw_description=desc,
        beneficiary=ben,
        doc_number=None,
        amount=Decimal(str(amount)),
        is_debit=is_debit,
        source='santander',
    )


def _comp(amount, cnpj, dt=None, name="FORNECEDOR TESTE"):
    a = Decimal(str(amount))
    return Comprovante(
        date=dt or date(2026, 1, 5),
        type='boleto',
        cnpj_beneficiary=cnpj,
        cnpj_final_beneficiary=None,
        beneficiary_name=name,
        amount_principal=a,
        amount_juros=Decimal('0'),
        amount_multa=Decimal('0'),
        amount_total=a,
        doc_number='12345',
        payer_cnpj='00000000000000',
        source='bradesco',
    )


def test_keyword_match_contamax():
    txs = [_tx("APLICACAO CONTAMAX", 5000)]
    results = ENGINE.match_all(txs, [])
    r = results[0]
    assert r.match_type == 'keyword'
    assert r.needs_review is False
    assert r.cod_deb == CFG.cod_contamax


def test_keyword_match_iof():
    txs = [_tx("IOF IMPOSTO OPERACOES FINANCEIRAS", 24.96)]
    results = ENGINE.match_all(txs, [])
    r = results[0]
    assert r.match_type == 'keyword'
    assert r.cod_deb == CFG.cod_iof


def test_comprovante_match_exact():
    tx = _tx("PAGAMENTO DE BOLETO OUTROS BANCOS", 1842.91)
    comp = _comp(1842.91, "12345678000195")
    results = ENGINE.match_all([tx], [comp])
    r = results[0]
    assert r.match_type == 'comprovante'
    assert r.needs_review is False
    assert r.cod_deb == "999"   # conta do fornecedor
    assert r.cod_cred == CFG.cod_banco_principal
    assert r.score >= 70


def test_comprovante_cnpj_not_in_plano():
    tx = _tx("PAGAMENTO DE BOLETO OUTROS BANCOS", 500.00)
    comp = _comp(500.00, "99999999000199")  # CNPJ desconhecido
    results = ENGINE.match_all([tx], [comp])
    r = results[0]
    assert r.match_type == 'comprovante_parcial'
    assert r.needs_review is True
    assert 'plano de contas' in r.review_reason.lower()


def test_unmatched_transaction():
    # Transação sem regra e sem padrão reconhecível → realmente sem match
    tx = _tx("LOTE CREDITO ESPECIAL 9999", 500.00, is_debit=False)
    results = ENGINE.match_all([tx], [])
    r = results[0]
    assert r.match_type == 'unmatched'
    assert r.needs_review is True


def test_pix_recebido_matched_by_layer1b():
    # Camada 1b: PIX RECEBIDO classifica automaticamente (conta genérica)
    tx = _tx("PIX RECEBIDO 12345678000195", 260.70, is_debit=False)
    results = ENGINE.match_all([tx], [])
    r = results[0]
    assert r.match_type in ('cnpj_desc', 'generic_rule')
    assert r.needs_review is False
    assert r.cod_deb == CFG.cod_banco_principal


def test_summary_auto_rate():
    txs = [
        _tx("APLICACAO CONTAMAX", 5000),
        _tx("RESGATE CONTAMAX AUTOMATICO", 5000, is_debit=False),
        _tx("PIX RECEBIDO 12345", 100, is_debit=False),  # layer 1b
    ]
    results = ENGINE.match_all(txs, [])
    stats = ENGINE.summary(results)
    assert stats['total'] == 3
    assert stats['auto_matched'] == 3
    assert stats['needs_review'] == 0
    assert stats['auto_rate'] == 100.0


import pytest
