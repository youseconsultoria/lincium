from datetime import date
from decimal import Decimal
import re

from src.models import Transaction
from src.matching.engine import MatchResult
from src.output.dominio import generate, generate_review_report


def _result(cod_deb, cod_cred, historico, needs_review=False, amount="1000.00",
            dt=None, is_debit=True, review_reason=None):
    tx = Transaction(
        date=dt or date(2026, 1, 2),
        raw_description=historico,
        beneficiary=None,
        doc_number=None,
        amount=Decimal(amount),
        is_debit=is_debit,
        source='santander',
    )
    return MatchResult(
        transaction=tx,
        matched_comprovante=None,
        cod_deb=cod_deb,
        cod_cred=cod_cred,
        historico=historico,
        score=90 if not needs_review else 0,
        match_type='keyword' if not needs_review else 'unmatched',
        needs_review=needs_review,
        review_reason=review_reason,
    )


EMPRESA_CNPJ = "09.113.951/0001-41"


def test_header_line():
    content = generate([], EMPRESA_CNPJ)
    assert content.startswith("|0000|09113951000141|")


def test_single_lote_x():
    results = [_result("374", "9", "TARIFA AVULSA ENVIO PIX")]
    content = generate(results, EMPRESA_CNPJ)
    lines = content.strip().split('\n')
    assert "|6000|X||||" in lines
    assert any("|6100|02/01/2026|374|9|1000,00||TARIFA AVULSA ENVIO PIX||||" in l for l in lines)


def test_date_format():
    results = [_result("374", "9", "TARIFA", dt=date(2026, 1, 15))]
    content = generate(results, EMPRESA_CNPJ)
    assert "15/01/2026" in content


def test_value_format_no_thousands():
    results = [_result("9", "504", "PIX RECEBIDO", amount="4999.00", is_debit=False)]
    content = generate(results, EMPRESA_CNPJ)
    assert "4999,00" in content
    assert "4.999" not in content  # sem separador de milhar


def test_unmatched_skipped_by_default():
    results = [
        _result("374", "9", "TARIFA"),
        _result(None, None, "PIX RECEBIDO", needs_review=True, review_reason="sem comprovante"),
    ]
    content = generate(results, EMPRESA_CNPJ, skip_unmatched=True)
    # Só 1 lote gerado (unmatched skipado)
    assert content.count("|6000|") == 1


def test_unmatched_included_when_flag_off():
    results = [
        _result(None, None, "PIX RECEBIDO", needs_review=True),
    ]
    # Com skip_unmatched=False, não deve gerar linha porque cod_deb/cod_cred são None
    # (generate() ainda verifica None)
    content = generate(results, EMPRESA_CNPJ, skip_unmatched=False)
    # Nenhuma linha 6100 gerada (sem contas resolvidas)
    assert "|6100|" not in content


def test_review_report_csv():
    results = [
        _result("374", "9", "TARIFA"),
        _result(None, None, "PIX RECEBIDO", needs_review=True, review_reason="sem match"),
    ]
    report = generate_review_report(results)
    assert "PIX RECEBIDO" in report
    assert "sem match" in report
    assert "TARIFA" not in report  # matched não aparece no relatório


def test_historico_uppercased():
    results = [_result("374", "9", "tarifa avulsa pix")]
    content = generate(results, EMPRESA_CNPJ)
    assert "TARIFA AVULSA PIX" in content


def test_matches_real_dominio_format():
    """Verifica estrutura contra os arquivos reais de importação do Domínio."""
    results = [
        _result("9", "504", "PIX RECEBIDO 07739287903", amount="4999.00", is_debit=False,
                dt=date(2025, 9, 2)),
        _result("32", "9", "APLICACAO CONTAMAX", amount="113.69",
                dt=date(2025, 9, 2)),
    ]
    content = generate(results, "09.113.951/0001-41")
    lines = [l for l in content.strip().split('\n') if l]

    assert lines[0] == "|0000|09113951000141|"
    assert lines[1] == "|6000|X||||"
    assert "|6100|02/09/2025|9|504|4999,00||PIX RECEBIDO 07739287903||||" in lines
    assert "|6100|02/09/2025|32|9|113,69||APLICACAO CONTAMAX||||" in lines
