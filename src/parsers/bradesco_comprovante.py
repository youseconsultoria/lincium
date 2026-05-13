"""
Parser para Comprovantes de Transação Bancária do Bradesco (NET EMPRESA).

Formato: PDF com um comprovante por página, campos rotulados "Campo: Valor".
Tipo suportado: Boleto de Cobrança.

Particularidades:
  - Juros e Multa declarados separadamente → split automático sem cálculo
  - CNPJ do Beneficiário sempre presente → matching direto com NF-e
  - Padrão FIDC: quando "Beneficiário Final" ≠ "Não informado", usar CNPJ do Final
  - Valor total = principal + juros + multa (quando há acréscimos)
"""

import re
from datetime import date
from decimal import Decimal
from typing import Optional

import pdfplumber

from ..models import Comprovante

_AMOUNT_RE = re.compile(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})')
_DATE_RE = re.compile(r'(\d{2}/\d{2}/\d{4})')
_CNPJ_RE = re.compile(r'\d{2,3}[\.\d]*\.\d{3}/\d{4}-\d{2}')
_NOT_FOUND = 'N.o informado'


def _parse_amount(s: str) -> Decimal:
    s = s.strip().replace('.', '').replace(',', '.')
    return Decimal(s) if s else Decimal('0')


def _parse_date(s: str) -> date:
    d, m, y = int(s[:2]), int(s[3:5]), int(s[6:])
    return date(y, m, d)


def _normalize_cnpj(s: str) -> str:
    """Remove formatação do CNPJ/CPF, retorna só dígitos."""
    return re.sub(r'[^\d]', '', s)


def _extract_field(text: str, label: str) -> Optional[str]:
    """Extrai valor de um campo rotulado 'label: valor' no texto."""
    pattern = re.compile(re.escape(label) + r'\s*[:\s]\s*(.+?)(?:\n|$)', re.IGNORECASE)
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _parse_page(text: str) -> Optional[Comprovante]:
    """Parseia uma página de comprovante Bradesco. Retorna None se não for boleto."""
    if 'Boleto de Cobran' not in text and 'boleto' not in text.lower():
        return None

    # Data da operação
    date_val = None
    m = re.search(r'Data da opera.{0,5}o:\s*(\d{2}/\d{2}/\d{4})', text)
    if m:
        date_val = _parse_date(m.group(1))

    # Número do documento
    doc_number = None
    m = re.search(r'Documento:\s*(\w+)', text)
    if m:
        doc_number = m.group(1)

    # Empresa / CNPJ do pagador
    payer_cnpj = ''
    m = re.search(r'CNPJ:\s*(' + _CNPJ_RE.pattern + r')', text)
    if m:
        payer_cnpj = _normalize_cnpj(m.group(1))

    # Beneficiário e CNPJ
    beneficiary_name = ''
    cnpj_beneficiary = ''
    cnpj_final = None

    # Linha "Razão Social Beneficiário:" (nome principal do beneficiário)
    m = re.search(r'Raz.o Social\s*\n?Benefici.rio:\s*\n?(.+?)(?:\n|$)', text)
    if m:
        beneficiary_name = m.group(1).strip()

    # CNPJ do beneficiário principal
    m = re.search(r'CPF/CNPJ Benefici.rio:\s*(' + _CNPJ_RE.pattern + r')', text)
    if m:
        cnpj_beneficiary = _normalize_cnpj(m.group(1))

    # Beneficiário Final (FIDC): o CNPJ aparece ANTES de "Final:" (linha quebrada no PDF)
    # Formato: "CPF/CNPJ Beneficiário NNN.NNN.NNN/NNNN-NN\nFinal:"
    m_final_cnpj = re.search(
        r'CPF/CNPJ Benefici.rio\s+(' + _CNPJ_RE.pattern + r')\s*\n\s*Final:',
        text,
    )
    if not m_final_cnpj:
        # fallback: formato normal "CPF/CNPJ Beneficiário Final: NNN..."
        m_final_cnpj = re.search(
            r'CPF/CNPJ Benefici.rio\s*\n?\s*Final:\s*(' + _CNPJ_RE.pattern + r')',
            text,
        )
    final_cnpj_text = m_final_cnpj.group(1).strip() if m_final_cnpj else ''
    if final_cnpj_text and not re.search(_NOT_FOUND, final_cnpj_text, re.IGNORECASE):
        cnpj_final = _normalize_cnpj(final_cnpj_text)

    # Valores
    def extract_amount(label: str) -> Decimal:
        m = re.search(re.escape(label) + r'[:\s]*R\$\s*(\d[\d.,]*)', text, re.IGNORECASE)
        if m:
            return _parse_amount(m.group(1))
        return Decimal('0')

    amount_principal = extract_amount('Valor R$')
    if amount_principal == Decimal('0'):
        # fallback: primeiro "Valor R$" na página
        m = _AMOUNT_RE.search(text)
        if m:
            amount_principal = _parse_amount(m.group(1))

    amount_juros = extract_amount('Juros:')
    amount_multa = extract_amount('Multa:')
    amount_total = extract_amount('Valor total:')
    if amount_total == Decimal('0'):
        amount_total = amount_principal + amount_juros + amount_multa

    if date_val is None or amount_total == Decimal('0'):
        return None

    return Comprovante(
        date=date_val,
        type='boleto',
        cnpj_beneficiary=cnpj_final or cnpj_beneficiary,
        cnpj_final_beneficiary=cnpj_final,
        beneficiary_name=beneficiary_name,
        amount_principal=amount_principal,
        amount_juros=amount_juros,
        amount_multa=amount_multa,
        amount_total=amount_total,
        doc_number=doc_number,
        payer_cnpj=payer_cnpj,
        source='bradesco',
    )


def parse_file(pdf_path: str) -> list[Comprovante]:
    """
    Faz o parse de um PDF de comprovantes Bradesco (uma ou várias páginas).
    Retorna um Comprovante por página válida.
    """
    comprovantes: list[Comprovante] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            result = _parse_page(text)
            if result:
                comprovantes.append(result)

    return comprovantes
