from decimal import Decimal

from tests.conftest import COMPROVANTES_DIR
from src.parsers.bradesco_comprovante import parse_file

PDF = COMPROVANTES_DIR / "Bradesco_06052026_161939.PDF"


def test_parsed_count():
    comps = parse_file(str(PDF))
    assert len(comps) == 16, f"Esperado 16 comprovantes, obtido {len(comps)}"


def test_all_boleto_type():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.type == "boleto"


def test_source():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.source == "bradesco"


def test_cnpj_beneficiary_not_empty():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.cnpj_beneficiary, f"CNPJ vazio: {c}"
        # Bradesco usa zero-padding no primeiro grupo: CNPJ pode ter 14 ou 15 dígitos
        assert c.cnpj_beneficiary.isdigit(), f"CNPJ com chars inválidos: {c.cnpj_beneficiary}"
        assert len(c.cnpj_beneficiary) in (11, 14, 15), f"Tamanho inválido: {c.cnpj_beneficiary}"


def test_amounts_positive():
    comps = parse_file(str(PDF))
    for c in comps:
        assert c.amount_total > Decimal("0"), f"Valor zero: {c}"


def test_payer_cnpj_consistent():
    comps = parse_file(str(PDF))
    # Todos os comprovantes são da mesma empresa (BARBOSA - ALUMINIO LTDA)
    # Bradesco usa zero-padding → "019617689000126" (15 dígitos)
    payers = {c.payer_cnpj for c in comps}
    assert len(payers) == 1, f"Múltiplos pagadores: {payers}"
    payer = payers.pop()
    assert "19617689" in payer, f"CNPJ do pagador inesperado: {payer}"


def test_fidc_uses_final_beneficiary():
    """Página 3 tem FIDC com beneficiário final diferente → deve usar CNPJ final."""
    comps = parse_file(str(PDF))
    # FIDC LEPAPIE (028.267.746/0001-85) com final SCHMIDT DISTRIBUIDORA (005.255.986/0001-64)
    fidc_comps = [c for c in comps if c.cnpj_final_beneficiary is not None]
    assert len(fidc_comps) >= 1, "Nenhum comprovante FIDC encontrado"
    for c in fidc_comps:
        # O CNPJ principal deve ser o do beneficiário FINAL
        assert c.cnpj_beneficiary == c.cnpj_final_beneficiary
        # CNPJ do FIDC (intermediário) deve ser diferente do CNPJ final
        # Verifica que não usou o CNPJ do FIDC como beneficiário
        assert "28267746" not in c.cnpj_beneficiary, "Usou CNPJ do FIDC ao invés do final"
