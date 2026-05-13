from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Transaction:
    date: date
    raw_description: str       # texto exato da coluna Descrição
    beneficiary: Optional[str] # linha continuação (nome do beneficiário, referência)
    doc_number: Optional[str]  # N° Documento
    amount: Decimal            # sempre positivo
    is_debit: bool
    saldo: Optional[Decimal] = None  # saldo corrente quando disponível
    source: str = "unknown"          # banco/tipo de documento de origem


@dataclass
class Comprovante:
    """Comprovante de pagamento (boleto ou PIX) — usado para matching com extrato."""
    date: date
    type: str                              # "boleto" | "pix"
    cnpj_beneficiary: str                  # CNPJ normalizado (só dígitos) para matching
    cnpj_final_beneficiary: Optional[str]  # FIDC: CNPJ do beneficiário real
    beneficiary_name: str
    amount_principal: Decimal
    amount_juros: Decimal
    amount_multa: Decimal
    amount_total: Decimal
    doc_number: Optional[str]              # N° do documento ou barcode
    payer_cnpj: str                        # CNPJ da empresa que pagou
    source: str = "unknown"
