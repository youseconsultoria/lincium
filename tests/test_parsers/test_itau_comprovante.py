from decimal import Decimal

from tests.conftest import COMPROVANTES_DIR
from src.parsers.itau_comprovante import parse_file

PDF = COMPROVANTES_DIR / "Extrato_0126_593771_itau - comprovantes - OK.pdf"


def test_parsed_count():
    comps = parse_file(str(PDF))
    assert len(comps) >= 30, f"Poucos comprovantes: {len(comps)}"


def test_types_are_pix_or_boleto():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.type in ("pix", "boleto"), f"Tipo inválido: {c.type}"


def test_source():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.source == "itau"


def test_cnpj_when_present_is_digits():
    """Quando CNPJ está presente, deve conter só dígitos. PIX para PF pode ter CNPJ vazio."""
    comps = parse_file(str(PDF))
    for c in comps:
        if c.cnpj_beneficiary:
            assert c.cnpj_beneficiary.isdigit(), f"CNPJ com chars inválidos: {c.cnpj_beneficiary}"


def test_boletos_have_cnpj():
    """Boletos sempre têm CNPJ do beneficiário (não tem chave mascarada)."""
    comps = parse_file(str(PDF))
    boletos = [c for c in comps if c.type == "boleto"]
    assert len(boletos) > 0
    for c in boletos:
        assert c.cnpj_beneficiary, f"Boleto sem CNPJ: {c}"


def test_amounts_positive():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.amount_total > Decimal("0"), f"Valor zero: {c}"


def test_payer_cnpj_consistent():
    comps = parse_file(str(PDF))
    # Todos são do mesmo pagador ZMA - PERFIL DE ALUMINIO LTDA (00.296.181/0001-45)
    for c in comps:
        assert "296181" in c.payer_cnpj, f"Pagador inesperado: {c.payer_cnpj}"


def test_boleto_total_equals_principal_plus_mora():
    comps = parse_file(str(PDF))
    boletos = [c for c in comps if c.type == "boleto"]
    for c in boletos:
        assert c.amount_total == c.amount_principal + c.amount_multa


def test_first_pix_amount():
    comps = parse_file(str(PDF))
    pix = [c for c in comps if c.type == "pix"]
    assert len(pix) > 0
    first = next((c for c in pix if c.amount_total == Decimal("1331.40")), None)
    assert first is not None, "PIX de R$1.331,40 não encontrado"
