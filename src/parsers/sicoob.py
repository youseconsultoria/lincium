"""
Parser para Extrato de Conta Corrente do Sicoob (SISBR).

Formato: PDF com layout de tabela — pdfplumber mistura colunas ao extrair texto.
Usa extração por posição de palavras (x/y) para reconstruir as colunas corretamente.

Colunas: DATA | HISTÓRICO | VALOR
Particularidades:
  - VALOR e indicador D/C aparecem na coluna direita (x ≥ 450 pt)
  - Devido ao layout, o valor pode ser extrato algumas linhas acima da descrição;
    o agrupamento por faixa de y-position resolve isso
  - Linhas SALDO ANTERIOR, SALDO DO DIA, SALDO BLOQ.* são descartadas
  - Continuações (Pagamento Pix, CNPJ, etc.) ficam abaixo da transação
"""

import re
from datetime import date
from decimal import Decimal
from typing import Optional

import pdfplumber

from ..models import Transaction

_DATE_RE = re.compile(r'^(\d{2})/(\d{2})$')
_AMOUNT_RE = re.compile(r'^(\d{1,3}(?:\.\d{3})*,\d{2})\*?$')
_DC_RE = re.compile(r'^[DC]$')

_SKIP_HIST = re.compile(
    r'^(SALDO|RESUMO|CHEQUE ESPECIAL|JUROS|TARIFAS|ENCARGOS|OUTRAS|VENCIMENTO|'
    r'TAXA|CUSTO|000 EXTRATOS|SAC:|OUVIDORIA|SISBR)',
    re.IGNORECASE
)

# Limites de colunas (pontos)
_X_DATA_MAX = 145
_X_HIST_MAX = 450
# Palavras com x >= _X_HIST_MAX pertencem à coluna VALOR/DC


def _group_words_by_row(words: list, y_tol: int = 11) -> list[list]:
    """Agrupa palavras por proximidade vertical (faixa de y-position)."""
    if not words:
        return []
    rows, current = [], [words[0]]
    ref_y = words[0]['top']
    for w in words[1:]:
        if abs(w['top'] - ref_y) <= y_tol:
            current.append(w)
        else:
            rows.append(current)
            current = [w]
            ref_y = w['top']
    if current:
        rows.append(current)
    return rows


def _parse_amount(s: str) -> Decimal:
    return Decimal(s.replace('.', '').replace(',', '.'))


def parse_file(pdf_path: str, year: int = None) -> list[Transaction]:
    """
    Faz o parse de um extrato de conta corrente do Sicoob.

    Args:
        pdf_path: Caminho para o PDF.
        year: Ano do extrato (inferido do cabeçalho "PERÍODO: DD/MM/YYYY" se omitido).

    Returns:
        Lista de Transaction (apenas movimentações, sem saldos).
    """
    transactions: list[Transaction] = []
    last_tx: Optional[Transaction] = None
    inferred_year = year

    with pdfplumber.open(pdf_path) as pdf:
        if inferred_year is None:
            # Extrai ano do campo "PERÍODO: DD/MM/YYYY - DD/MM/YYYY"
            for pg in pdf.pages[:2]:
                text = pg.extract_text() or ''
                m = re.search(r'PER.ODO:\s+\d{2}/\d{2}/(\d{4})', text)
                if m:
                    inferred_year = int(m.group(1))
                    break
            if inferred_year is None:
                from datetime import datetime
                inferred_year = datetime.now().year

        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            rows = _group_words_by_row(words, y_tol=11)

            for row in rows:
                data_words = [w for w in row if w['x0'] < _X_DATA_MAX]
                hist_words = [w for w in row if _X_DATA_MAX <= w['x0'] < _X_HIST_MAX]
                valor_words = [w for w in row if w['x0'] >= _X_HIST_MAX]

                # Identifica linhas com data válida na coluna DATA
                data_text = ' '.join(w['text'] for w in data_words)
                dm = _DATE_RE.match(data_text.strip())
                if not dm:
                    # Linha de continuação (detalhes do Pix, CNPJ, etc.)
                    if last_tx is not None and hist_words:
                        cont = ' '.join(w['text'] for w in hist_words)
                        # Guarda o primeiro detalhe não vazio como beneficiary
                        if last_tx.beneficiary is None and cont.strip():
                            last_tx.beneficiary = cont.strip()
                    continue

                hist_text = ' '.join(w['text'] for w in hist_words).strip()
                valor_text = ' '.join(w['text'] for w in valor_words).strip()

                if _SKIP_HIST.match(hist_text):
                    continue

                # Extrai valor e D/C da coluna VALOR
                # valor_text pode ser: "128,30 D", "308,26 C", "0,00* C", "51,66C"
                # Trata D/C colado ao valor (ex: "51,66C")
                combined = re.match(r'^(\d{1,3}(?:\.\d{3})*,\d{2})\*?([DC])$', valor_text)
                if combined:
                    amount_str, dc = combined.group(1), combined.group(2)
                elif ' ' in valor_text:
                    parts = valor_text.split()
                    amount_str = parts[0].rstrip('*')
                    dc = parts[-1] if parts[-1] in ('D', 'C') else None
                else:
                    amount_str = valor_text.rstrip('*DC')
                    dc_match = re.search(r'[DC]$', valor_text.rstrip('*'))
                    dc = dc_match.group() if dc_match else None

                if not _AMOUNT_RE.match(amount_str.rstrip('DC')):
                    continue
                if dc not in ('D', 'C'):
                    continue

                day, month = int(dm.group(1)), int(dm.group(2))
                tx = Transaction(
                    date=date(inferred_year, month, day),
                    raw_description=hist_text,
                    beneficiary=None,
                    doc_number=None,
                    amount=_parse_amount(amount_str),
                    is_debit=(dc == 'D'),
                    source='sicoob',
                )
                transactions.append(tx)
                last_tx = tx

    return transactions
