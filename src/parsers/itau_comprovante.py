"""
Parser para Comprovantes do Itaú Unibanco (NET EMPRESA / Sispag).

Formato: PDF com dois tipos de comprovante por arquivo:
  - "Comprovante de Transferência" → PIX
  - "Comprovante de pagamento de boleto" → Boleto

Particularidades PIX:
  - CNPJ do recebedor em "CPF / CNPJ do recebedor:"
  - Caso pagador == recebedor: transferência interna (contas próprias)
  - Identificação no comprovante pode estar vazia (usar ID da transação)
  - "chave" pode ser CNPJ/CPF numérico → extrair como CNPJ do beneficiário

Particularidades Boleto:
  - CNPJ na linha "Razão Social: NOME  CNPJ  DATA" (mesclado pela extração)
  - Mora/Multa combinados em um único campo "(+)Mora/Multa"
  - Beneficiário Final opcional (padrão FIDC)
  - "Valor do boleto" = principal (sem mora); "Valor do pagamento" = total
"""

import re
from datetime import date
from decimal import Decimal
from typing import Optional

import pdfplumber

from ..models import Comprovante

_CNPJ_PATTERN = r'\d{2,3}[\.\d]*\.\d{3}/\d{4}-\d{2}'
_DATE_PATTERN = r'\d{2}/\d{2}/\d{4}'
_AMOUNT_PATTERN = r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})'


def _normalize_cnpj(s: str) -> str:
    return re.sub(r'[^\d]', '', s)


def _parse_amount(s: str) -> Decimal:
    s = s.strip().replace('.', '').replace(',', '.')
    return Decimal(s) if s else Decimal('0')


def _parse_date(s: str) -> date:
    d, m, y = int(s[:2]), int(s[3:5]), int(s[6:])
    return date(y, m, d)


def _extract(text: str, label: str) -> Optional[str]:
    m = re.search(re.escape(label) + r'\s*[:\s]\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_pix(text: str, payer_cnpj: str) -> Optional[Comprovante]:
    # Data
    m = re.search(r'data da transfer.{0,6}ncia:\s*(' + _DATE_PATTERN + r')', text, re.IGNORECASE)
    if not m:
        return None
    tx_date = _parse_date(m.group(1))

    # Valor
    m = re.search(r'valor:\s*' + _AMOUNT_PATTERN, text, re.IGNORECASE)
    if not m:
        return None
    amount = _parse_amount(m.group(1))

    # CNPJ do recebedor — pode vir de "CPF / CNPJ do recebedor:" ou da "chave"
    cnpj_beneficiary = ''
    m = re.search(r'CPF\s*/\s*CNPJ do recebedor:\s*(' + _CNPJ_PATTERN + r')', text, re.IGNORECASE)
    if m:
        cnpj_beneficiary = _normalize_cnpj(m.group(1))
    else:
        # tenta chave numérica (CNPJ/CPF sem formatação)
        m = re.search(r'chave:\s*(\d{11,14})\b', text, re.IGNORECASE)
        if m:
            cnpj_beneficiary = m.group(1)

    # Nome do recebedor
    beneficiary_name = _extract(text, 'nome do recebedor') or ''

    # Identificação no comprovante
    doc_number = _extract(text, 'identifica.{0,5}o no comprovante') or None
    if doc_number == '':
        doc_number = None

    return Comprovante(
        date=tx_date,
        type='pix',
        cnpj_beneficiary=cnpj_beneficiary,
        cnpj_final_beneficiary=None,
        beneficiary_name=beneficiary_name,
        amount_principal=amount,
        amount_juros=Decimal('0'),
        amount_multa=Decimal('0'),
        amount_total=amount,
        doc_number=doc_number,
        payer_cnpj=payer_cnpj,
        source='itau',
    )


def _parse_boleto(text: str, payer_cnpj: str) -> Optional[Comprovante]:
    # Data de pagamento
    m = re.search(r'Data de pagamento:\s*(' + _DATE_PATTERN + r')', text, re.IGNORECASE)
    if not m:
        return None
    tx_date = _parse_date(m.group(1))

    # Valor do boleto (principal, sem mora)
    m_princ = re.search(r'Valor do boleto.*?[;\s]\s*(\d{1,3}(?:\.\d{3})*,\d{2})', text, re.IGNORECASE | re.DOTALL)
    amount_principal = _parse_amount(m_princ.group(1)) if m_princ else Decimal('0')

    # Mora/Multa
    m_mora = re.search(r'Mora/Multa.*?' + _AMOUNT_PATTERN, text, re.IGNORECASE | re.DOTALL)
    amount_mora = _parse_amount(m_mora.group(1)) if m_mora else Decimal('0')

    # Valor total do pagamento
    m_total = re.search(r'Valor do pagamento.*?' + _AMOUNT_PATTERN, text, re.IGNORECASE | re.DOTALL)
    amount_total = _parse_amount(m_total.group(1)) if m_total else (amount_principal + amount_mora)

    # CNPJ do beneficiário — na linha "Razão Social: NOME  CNPJ  DATA"
    # Formato: "Razão Social: NOME  NN.NNN.NNN/NNNN-NN  DD/MM/YYYY"
    cnpj_beneficiary = ''
    beneficiary_name = ''
    m_razao = re.search(r'Raz.o Social:\s+(.+?)\s+(' + _CNPJ_PATTERN + r')\s+' + _DATE_PATTERN, text, re.IGNORECASE)
    if m_razao:
        beneficiary_name = m_razao.group(1).strip()
        cnpj_beneficiary = _normalize_cnpj(m_razao.group(2))

    # Beneficiário Final (FIDC)
    cnpj_final = None
    m_final = re.search(r'CPF/CNPJ do benefici.rio final:\s*(' + _CNPJ_PATTERN + r')', text, re.IGNORECASE)
    if m_final:
        cnpj_final_raw = m_final.group(1).strip()
        if not re.search(r'N.o informado', cnpj_final_raw, re.IGNORECASE):
            cnpj_final = _normalize_cnpj(cnpj_final_raw)
    else:
        # CNPJ final pode aparecer em linha separada após "Beneficiário Final:"
        m_final_block = re.search(
            r'Benefici.rio Final:.*?\n(.+?)\n(' + _CNPJ_PATTERN + r')',
            text, re.IGNORECASE | re.DOTALL
        )
        if m_final_block:
            candidate = _normalize_cnpj(m_final_block.group(2))
            if candidate != _normalize_cnpj(cnpj_beneficiary):
                cnpj_final = candidate

    # Identificação no comprovante (barcode ou código)
    doc_number = None
    m_id = re.search(r'Identifica.{0,5}o no meu comprovante:\s*\n(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m_id:
        doc_number = m_id.group(1).strip()

    if not cnpj_beneficiary:
        return None

    return Comprovante(
        date=tx_date,
        type='boleto',
        cnpj_beneficiary=cnpj_final or cnpj_beneficiary,
        cnpj_final_beneficiary=cnpj_final,
        beneficiary_name=beneficiary_name,
        amount_principal=amount_principal,
        amount_juros=Decimal('0'),
        amount_multa=amount_mora,
        amount_total=amount_total,
        doc_number=doc_number,
        payer_cnpj=payer_cnpj,
        source='itau',
    )


def parse_file(pdf_path: str) -> list[Comprovante]:
    """
    Faz o parse de um PDF de comprovantes Itaú (PIX + boleto misturados).
    Retorna um Comprovante por página válida.
    """
    comprovantes: list[Comprovante] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # Extrai CNPJ do pagador (constante em todas as páginas do arquivo)
            payer_cnpj = ''
            m = re.search(r'CPF(?:\s*/\s*|/)CNPJ(?:\s+do\s+pagador)?:\s*(' + _CNPJ_PATTERN + r')', text, re.IGNORECASE)
            if m:
                payer_cnpj = _normalize_cnpj(m.group(1))

            first_line = text.split('\n')[0].strip() if text else ''

            if 'Transfer' in first_line or 'transfer' in first_line:
                result = _parse_pix(text, payer_cnpj)
            elif 'boleto' in first_line.lower():
                result = _parse_boleto(text, payer_cnpj)
            else:
                result = None

            if result:
                comprovantes.append(result)

    return comprovantes
