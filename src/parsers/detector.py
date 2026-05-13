"""
Detecta automaticamente o banco/formato de um PDF e retorna a função de parse correta.
Evita que o chamador precise saber qual parser usar para cada arquivo.
"""

from typing import Callable
import pdfplumber

from .santander import parse_file as parse_santander
from .banco_do_brasil import parse_file as parse_banco_do_brasil
from .sicoob import parse_file as parse_sicoob
from .bradesco_comprovante import parse_file as parse_bradesco_comprovante
from .itau_comprovante import parse_file as parse_itau_comprovante


def detect_and_parse(pdf_path: str, **kwargs) -> list:
    """
    Abre o PDF, detecta o banco/tipo e retorna a lista de Transaction ou Comprovante.
    Passa kwargs adicionais para o parser (ex: year=2026).
    """
    parser = detect_parser(pdf_path)
    return parser(pdf_path, **kwargs)


def detect_parser(pdf_path: str) -> Callable:
    """
    Retorna a função de parse adequada para o PDF informado.
    Raises ValueError se o formato não for reconhecido.
    """
    with pdfplumber.open(pdf_path) as pdf:
        first_text = (pdf.pages[0].extract_text() or '').upper()
        # Para arquivos de comprovante, verifica também a segunda página
        second_text = ''
        if len(pdf.pages) > 1:
            second_text = (pdf.pages[1].extract_text() or '').upper()

    combined = first_text + ' ' + second_text

    # Extratos bancários
    if 'SANTANDER' in combined and 'EXTRATO CONSOLIDADO' in combined:
        return parse_santander

    # O PDF do BB não menciona "BANCO DO BRASIL" no texto — usa marcadores estruturais únicos
    if 'EXTRATO DE CONTA CORRENTE' in combined and 'SICOOB' not in combined and 'SANTANDER' not in combined:
        return parse_banco_do_brasil

    if 'SICOOB' in combined or 'SISBR' in combined:
        return parse_sicoob

    # Comprovantes
    if 'BRADESCO' in combined and ('BOLETO DE COBRAN' in combined or 'COMPROVANTE DE TRANSA' in combined):
        return parse_bradesco_comprovante

    if ('COMPROVANTE DE TRANSFER' in combined or 'COMPROVANTE DE PAGAMENTO DE BOLETO' in combined) and (
        'ITAU' in combined or 'SISPAG' in combined or 'AGÊNCIA/CONTA:0126' in combined
    ):
        return parse_itau_comprovante

    raise ValueError(
        f"Formato de PDF não reconhecido. Adicione suporte para: {pdf_path}\n"
        f"Texto encontrado: {combined[:200]}"
    )
