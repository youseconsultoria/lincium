"""
Gerador de arquivo de importação para o Domínio Sistemas.

Formato pipe-delimited (não é XML, apesar da extensão .txt):
  |0000|CNPJ_EMPRESA|
  |6000|TIPO||||
  |6100|DD/MM/YYYY|COD_DEB|COD_CRED|VALOR||HISTORICO||||

Tipos de 6000:
  X = 1 débito : 1 crédito  (caso geral — MVP)
  C = 1 crédito : N débitos  (split de juros — v1)
  D = N débitos : 1 crédito
  V = N débitos : N créditos

Data: DD/MM/YYYY (barra separando)
Valor: decimal com vírgula, sem separador de milhar (ex: 4999,00)
Campos 8, 9, 10 do 6100: sempre vazios → "||||" no final
"""

from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Optional

from ..matching.engine import MatchResult
from ..models import Comprovante


def _fmt_date(d: date) -> str:
    return d.strftime('%d/%m/%Y')


def _fmt_value(v: Decimal) -> str:
    # Domínio usa vírgula decimal, sem separador de milhar
    return str(v.quantize(Decimal('0.01'))).replace('.', ',')


def _lote_x(
    dt: date, cod_deb: str, cod_cred: str, valor: Decimal, historico: str
) -> str:
    hist = historico[:40].upper()
    return (
        f"|6000|X||||\n"
        f"|6100|{_fmt_date(dt)}|{cod_deb}|{cod_cred}|{_fmt_value(valor)}||{hist}||||\n"
    )


def _lote_c(
    dt: date,
    splits: list[tuple[str, str, Decimal, str]],  # (cod_deb, cod_cred, valor, hist)
) -> str:
    """Gera bloco tipo C (split — ex: principal + juros)."""
    lines = ["|6000|C||||\n"]
    for cod_deb, cod_cred, valor, hist in splits:
        hist = hist[:40].upper()
        lines.append(f"|6100|{_fmt_date(dt)}|{cod_deb}|{cod_cred}|{_fmt_value(valor)}||{hist}||||\n")
    return ''.join(lines)


def generate(
    results: list[MatchResult],
    empresa_cnpj: str,
    output_path: Optional[str | Path] = None,
    skip_unmatched: bool = True,
    cod_banco: Optional[str] = None,
    cod_juros: Optional[str] = None,
    cod_multa: Optional[str] = None,
) -> str:
    """
    Gera o conteúdo do arquivo de importação Domínio.

    Args:
        results:         Lista de MatchResult do motor de matching.
        empresa_cnpj:    CNPJ da empresa (vai no |0000|).
        output_path:     Se informado, salva o arquivo neste caminho.
        skip_unmatched:  Se True, omite lançamentos sem conta resolvida.
        cod_banco:       Código da conta bancária (para splits com juros).
        cod_juros:       Código da conta de juros (para splits — opcional).
        cod_multa:       Código da conta de multa (para splits — opcional).

    Returns:
        Conteúdo do arquivo como string.
    """
    buf = StringIO()
    cnpj_digits = empresa_cnpj.replace('.', '').replace('/', '').replace('-', '')
    buf.write(f"|0000|{cnpj_digits}|\n")

    emitted = 0
    skipped = 0

    for r in results:
        # Nunca gera linha com contas None, independente do flag
        if r.cod_deb is None or r.cod_cred is None:
            skipped += 1
            continue
        # Pula revisões humanas se skip_unmatched=True
        if r.needs_review and skip_unmatched:
            skipped += 1
            continue

        # Verifica se há split de juros/multa disponível via comprovante
        comp = r.matched_comprovante
        if (
            comp
            and cod_banco
            and cod_juros
            and (comp.amount_juros > Decimal('0') or comp.amount_multa > Decimal('0'))
        ):
            # Tipo C: principal + juros + multa
            splits = [(r.cod_deb, r.cod_cred, comp.amount_principal, r.historico)]
            if comp.amount_juros > Decimal('0'):
                splits.append((cod_juros, cod_banco, comp.amount_juros, 'JUROS BOLETO'))
            if comp.amount_multa > Decimal('0') and cod_multa:
                splits.append((cod_multa, cod_banco, comp.amount_multa, 'MULTA BOLETO'))
            buf.write(_lote_c(r.transaction.date, splits))
        else:
            buf.write(_lote_x(
                r.transaction.date,
                r.cod_deb,
                r.cod_cred,
                r.transaction.amount,
                r.historico,
            ))
        emitted += 1

    content = buf.getvalue()

    if output_path:
        Path(output_path).write_text(content, encoding='latin-1')

    return content


def generate_review_report(
    results: list[MatchResult],
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Gera relatório CSV das transações que precisam de revisão humana.
    """
    lines = ['data,valor,debito,descricao,beneficiario,motivo\n']
    for r in results:
        if not r.needs_review:
            continue
        tx = r.transaction
        row = (
            f"{_fmt_date(tx.date)},"
            f"{_fmt_value(tx.amount)},"
            f"{'S' if tx.is_debit else 'N'},"
            f'"{tx.raw_description[:50]}",'
            f'"{(tx.beneficiary or "")[:30]}",'
            f'"{(r.review_reason or "")[:60]}"\n'
        )
        lines.append(row)

    content = ''.join(lines)
    if output_path:
        Path(output_path).write_text(content, encoding='utf-8')
    return content
