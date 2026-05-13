"""
Parser para Extrato Consolidado Inteligente do Santander PJ.

Formato: PDF com tabela Data | Descrição | N° Documento | Créditos | Débitos | Saldo
Particularidades:
  - Data aparece UMA VEZ por dia (primeira transação do dia); propagada para as seguintes
  - Descrições podem ter linha de continuação (nome do beneficiário, referência)
  - Crédito e Débito em colunas separadas; débito sinalizado por '-' no final do valor
  - CONTAMAX: investimento overnight — saldo fecha R$0,00 por dia (normal, não erro)
  - GETNET: recebimentos de maquininha = CRÉDITO (nome confunde)
  - ContaMax: aplicação automática ao final do dia + resgate na manhã seguinte
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pdfplumber

from ..models import Transaction

# --- Regex ---

_DATE_PREFIX = re.compile(r'^(\d{2}/\d{2}) (.*)', re.DOTALL)
_AMOUNT = r'\d{1,3}(?:\.\d{3})*,\d{2}'
# Linha com saldo explícito: ocorre no RESGATE CONTAMAX (balance = 0,00 ao final)
_TWO_AMOUNTS = re.compile(rf'({_AMOUNT}-?)\s+({_AMOUNT})$')
_ONE_AMOUNT = re.compile(rf'({_AMOUNT}-?)$')
# Doc number = dígitos OU hífen, sempre antes do valor na mesma linha
_DOC_NUMBER = re.compile(r'\s+(-|\d+)$')

# Linhas a ignorar: cabeçalhos, rodapés, resumo de conta e texto institucional
_SKIP = re.compile(
    r'^('
    r'Data\s+Descri'
    r'|Cr.ditos\s*D'
    r'|EXTRATO CONSOLIDADO'
    r'|[A-Za-z]+/20\d{2}$'          # "janeiro/2026"
    r'|Extrato_PJ'
    r'|BALP_'
    r'|Pagina:'
    r'|\(=\)|\(\+\)|\(-\)'          # linhas de total/saldo resumido
    r'|Dep'                          # "Depósitos / Transferências"
    r'|Outros (?:Cr|D)'              # "Outros Créditos/Débitos"
    r'|Pagamentos /'                 # "Pagamentos / Transferências"
    r'|Limite Santander'
    r'|Saldo de Investimentos'
    r'|Saldo Dispon'
    r'|Fale Conosco'
    r'|Central de Atend'
    r'|Resumo -'
    r'|Movimenta'
    r'|Conta Corrente$'
    r'|De segunda'
    r'|4004 2125'
    r'|0800 '
    r'|Acesse:'
    r'|Ouvidoria'
    r'|Para contrata'
    r'|No exterior'
    r'|Libras \('
    r'|Prezado'
    r'|Solu.es em'
    r')',
    re.IGNORECASE,
)

# Linhas que não são continuação de transação (não adicionar como beneficiário)
_NOT_CONTINUATION = re.compile(
    r'^(Data\s+Descri|Extrato_PJ|BALP_|Pagina:|EXTRATO CONSOLIDADO'
    r'|[A-Za-z]+/20\d{2}$|Cr.ditos|Solu.es|Fale Conosco|De segunda)',
    re.IGNORECASE,
)

# Marca fim da seção de transações ("SALDO EM DD/MM valor")
_SALDO_EM = re.compile(r'^SALDO EM\s+\d{2}/\d{2}')


def _parse_amount(s: str) -> Decimal:
    return Decimal(s.replace('.', '').replace(',', '.'))


def _extract_year(pdf) -> int:
    """Extrai o ano do cabeçalho do extrato (ex: 'Resumo - janeiro/2026')."""
    month_re = re.compile(
        r'(?:janeiro|fevereiro|mar.o|abril|maio|junho|julho|agosto'
        r'|setembro|outubro|novembro|dezembro)/(\d{4})',
        re.IGNORECASE,
    )
    for page in pdf.pages[:3]:
        text = page.extract_text() or ''
        m = month_re.search(text)
        if m:
            return int(m.group(1))
    return datetime.now().year


def _parse_line(line: str) -> Optional[dict]:
    """
    Tenta extrair uma transação de uma linha de texto.
    Retorna dict com campos ou None se a linha não for transação.
    """
    line = line.rstrip()

    if _SKIP.match(line):
        return None

    date_str = None
    m = _DATE_PREFIX.match(line)
    if m:
        date_str = m.group(1)
        line = m.group(2)

    # Detecta uma ou duas colunas de valor no final da linha
    m2 = _TWO_AMOUNTS.search(line)
    m1 = _ONE_AMOUNT.search(line)

    if m2:
        amount_str = m2.group(1)
        saldo_str = m2.group(2)
        remainder = line[: m2.start()].strip()
    elif m1:
        amount_str = m1.group(1)
        saldo_str = None
        remainder = line[: m1.start()].strip()
    else:
        return None  # linha de continuação (nome do beneficiário, etc.)

    is_debit = amount_str.endswith('-')
    amount = _parse_amount(amount_str.rstrip('-'))
    saldo = _parse_amount(saldo_str) if saldo_str else None

    m_doc = _DOC_NUMBER.search(remainder)
    if m_doc:
        doc_number = m_doc.group(1)
        description = remainder[: m_doc.start()].strip()
    else:
        doc_number = None
        description = remainder

    if not description:
        return None

    return {
        'date_str': date_str,
        'description': description,
        'doc_number': doc_number,
        'amount': amount,
        'is_debit': is_debit,
        'saldo': saldo,
    }


def parse_file(pdf_path: str, year: int = None) -> list[Transaction]:
    """
    Faz o parse de um PDF Santander Extrato Consolidado Inteligente PJ.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        year: Ano do extrato (inferido automaticamente do cabeçalho se omitido).

    Returns:
        Lista de Transaction ordenada cronologicamente.
    """
    transactions: list[Transaction] = []
    current_date: Optional[date] = None
    last_tx: Optional[Transaction] = None

    # Conta ocorrências de "SALDO EM DD/MM" para delimitar a seção de transações.
    # A primeira ocorrência é o saldo de abertura (início do mês anterior).
    # A segunda é o saldo de fechamento (fim do mês corrente) — para aqui.
    saldo_em_count = 0
    done = False

    with pdfplumber.open(pdf_path) as pdf:
        if year is None:
            year = _extract_year(pdf)

        for page in pdf.pages:
            if done:
                break

            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.rstrip()
                if not line:
                    continue

                # Delimitadores de seção
                if _SALDO_EM.match(line):
                    saldo_em_count += 1
                    if saldo_em_count >= 2:
                        done = True
                        break
                    continue

                parsed = _parse_line(line)

                if parsed is None:
                    # Linha de continuação: nome do beneficiário, referência, etc.
                    if last_tx is not None and not _NOT_CONTINUATION.match(line.strip()):
                        if last_tx.beneficiary is None:
                            last_tx.beneficiary = line.strip()
                    continue

                if parsed['date_str']:
                    day = int(parsed['date_str'][:2])
                    month = int(parsed['date_str'][3:5])
                    current_date = date(year, month, day)

                if current_date is None:
                    continue

                tx = Transaction(
                    date=current_date,
                    raw_description=parsed['description'],
                    beneficiary=None,
                    doc_number=parsed['doc_number'],
                    amount=parsed['amount'],
                    is_debit=parsed['is_debit'],
                    saldo=parsed['saldo'],
                    source='santander',
                )
                transactions.append(tx)
                last_tx = tx

    return transactions
