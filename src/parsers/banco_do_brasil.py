"""
Parser para Extrato de Conta Corrente do Banco do Brasil.

Formato: PDF com tabela pipe-delimited (lida como texto)
Colunas: Dt.balancete | Dt.movimento | Ag.origem | Lote | Histórico | Documento | Valor R$ | Saldo

Particularidades:
  - Data em formato DD/MM/YYYY (ano completo — sem necessidade de inferir o ano)
  - D/C na coluna imediatamente após o valor ('D' = débito, 'C' = crédito)
  - Saldo aparece após o D/C principal (ex: "232,30 D 2.981,45 C")
  - Linhas "Saldo Anterior" e "S A L D O" são descartadas
  - Continuações (ex: "Cobrança referente DD/MM/YYYY") aparecem como linha separada
"""

import re
from datetime import date
from decimal import Decimal
from typing import Optional

import pdfplumber

from ..models import Transaction

# Linha de transação: DD/MM/YYYY  AAAA  LLLLL  NNN  DESCRIPTION [DOC]  AMOUNT  D/C  [SALDO D/C]
_TX_LINE = re.compile(
    r'^(\d{2}/\d{2}/\d{4})\s+'       # data completa
    r'\d{4}\s+'                        # agência origem
    r'\d+\s+'                          # lote
    r'\d+\s+'                          # seq
    r'(.+?)\s+'                        # historico (lazy — captura desc + eventual doc)
    r'(\d{1,3}(?:\.\d{3})*,\d{2})\s+' # valor
    r'([DC])'                          # D/C
    r'(?:\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+[DC])?'  # saldo (ignorado)
    r'\s*$'
)

_SKIP_DESC = re.compile(
    r'^(Saldo Anterior|S\s+A\s+L\s+D\s+O|SALDO)',
    re.IGNORECASE
)

_NOT_CONTINUATION = re.compile(
    r'^(Ag\.|Per.odo|Lan.amentos|Dt\.|Cobran.as|Visualizar|Consultas|Extrato|Cliente|'
    r'OBSERVA|Transa.ao|SAC|0800)',
    re.IGNORECASE
)


def _parse_date(s: str) -> date:
    day, month, year = int(s[:2]), int(s[3:5]), int(s[6:])
    return date(year, month, day)


def _parse_amount(s: str) -> Decimal:
    return Decimal(s.replace('.', '').replace(',', '.'))


def parse_file(pdf_path: str) -> list[Transaction]:
    """
    Faz o parse de um extrato de conta corrente do Banco do Brasil.
    O ano é extraído diretamente do campo de data (DD/MM/YYYY).

    Returns:
        Lista de Transaction (apenas movimentações, sem saldos).
    """
    transactions: list[Transaction] = []
    last_tx: Optional[Transaction] = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.rstrip()
                if not line:
                    continue

                m = _TX_LINE.match(line)
                if not m:
                    if last_tx is not None and not _NOT_CONTINUATION.match(line.strip()):
                        if last_tx.beneficiary is None:
                            last_tx.beneficiary = line.strip()
                    continue

                date_str, description, amount_str, dc = (
                    m.group(1), m.group(2), m.group(3), m.group(4)
                )

                if _SKIP_DESC.match(description.strip()):
                    continue

                tx = Transaction(
                    date=_parse_date(date_str),
                    raw_description=description.strip(),
                    beneficiary=None,
                    doc_number=None,
                    amount=_parse_amount(amount_str),
                    is_debit=(dc == 'D'),
                    source='banco_do_brasil',
                )
                transactions.append(tx)
                last_tx = tx

    return transactions
