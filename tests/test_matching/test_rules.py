from datetime import date
from decimal import Decimal

from src.models import Transaction
from src.matching.rules import RuleSet, EmpresaConfig

CFG = EmpresaConfig.stub()
RULES = RuleSet(CFG)


def _tx(desc: str, is_debit=True, beneficiary=None, amount="100.00"):
    return Transaction(
        date=date(2026, 1, 5),
        raw_description=desc,
        beneficiary=beneficiary,
        doc_number=None,
        amount=Decimal(amount),
        is_debit=is_debit,
        source='santander',
    )


def test_contamax_aplicacao():
    r = RULES.match(_tx("APLICACAO CONTAMAX"))
    assert r is not None
    assert r.rule_name == "contamax_aplicacao"
    assert r.cod_deb == CFG.cod_contamax
    assert r.cod_cred == CFG.cod_banco_principal


def test_contamax_resgate():
    r = RULES.match(_tx("RESGATE CONTAMAX AUTOMATICO", is_debit=False))
    assert r is not None
    assert r.rule_name == "contamax_resgate"
    assert r.cod_deb == CFG.cod_banco_principal
    assert r.cod_cred == CFG.cod_contamax


def test_tarifa_avulsa():
    r = RULES.match(_tx("TARIFA AVULSA ENVIO PIX 02/01/2026"))
    assert r is not None
    assert r.rule_name == "tarifa"
    assert r.cod_deb == CFG.cod_tarifas


def test_tarifa_manutencao():
    r = RULES.match(_tx("TARIFA MANUTENCAO TIT VENCIDO"))
    assert r is not None
    assert r.rule_name == "tarifa"


def test_iof():
    r = RULES.match(_tx("IOF IMPOSTO OPERACOES FINANCEIRAS"))
    assert r is not None
    assert r.rule_name == "iof"
    assert r.cod_deb == CFG.cod_iof


def test_getnet_via_beneficiary():
    r = RULES.match(_tx("PAGAMENTO CARTAO DE DEBITO", beneficiary="GETNET-VISA ELECTR", is_debit=False))
    assert r is not None
    assert r.rule_name == "getnet"
    assert r.cod_cred == CFG.cod_receita_cartao


def test_darf():
    r = RULES.match(_tx("PAGAMENTO DARF EM CANAIS"))
    assert r is not None
    assert r.rule_name == "darf"
    assert r.cod_deb == CFG.cod_darf


def test_pix_recebido_no_rule():
    # PIX RECEBIDO genérico não tem regra na camada 0 — precisa de comprovante
    r = RULES.match(_tx("PIX RECEBIDO 60409075000152", is_debit=False))
    assert r is None


def test_pagamento_boleto_no_rule():
    # Boleto também não — precisa de comprovante
    r = RULES.match(_tx("PAGAMENTO DE BOLETO OUTROS BANCOS", beneficiary="FORNECEDOR XYZ"))
    assert r is None
