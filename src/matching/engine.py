"""
Motor de matching principal.

Arquitetura em camadas (camadas superiores têm prioridade):
  Camada 0 — Regras determinísticas por palavra-chave (implementada)
  Camada 1 — Match por CNPJ via comprovante + plano de contas (implementada)
  Camada 2 — Fuzzy matching por nome (v2)
  Camada 3 — Revisão humana

Score mínimo para auto-match via comprovante: 70 pts
  +40  valor exato
  +30  data igual
  +15  data ±1 dia
  +20  CNPJ confirmado via comprovante
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from ..models import Transaction, Comprovante
from .plano_de_contas import PlanoDeContas
from .rules import RuleSet, EmpresaConfig, RuleMatch


@dataclass
class MatchResult:
    transaction: Transaction
    matched_comprovante: Optional[Comprovante]
    cod_deb: Optional[str]
    cod_cred: Optional[str]
    historico: str
    score: int                  # 0-100
    match_type: str             # "keyword" | "comprovante" | "fuzzy" | "unmatched"
    needs_review: bool
    review_reason: Optional[str] = None


class MatchEngine:
    """
    Recebe uma lista de Transaction (extrato bancário) e uma lista de Comprovante
    (comprovantes de pagamento) e tenta associar cada Transaction às contas corretas
    do plano de contas, gerando MatchResult prontos para exportação.
    """

    def __init__(
        self,
        config: EmpresaConfig,
        plano: PlanoDeContas,
    ):
        self._config = config
        self._plano = plano
        self._rules = RuleSet(config)

    def match_all(
        self,
        transactions: list[Transaction],
        comprovantes: list[Comprovante],
    ) -> list[MatchResult]:
        """
        Processa todas as transações e retorna MatchResult para cada uma.
        Comprovantes são indexados internamente para busca eficiente.
        """
        # Índice de comprovantes por (data, valor_total arredondado) para busca rápida
        comp_index = self._build_comp_index(comprovantes)
        results = []
        for tx in transactions:
            results.append(self._match_single(tx, comp_index))
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_comp_index(
        self, comprovantes: list[Comprovante]
    ) -> dict[tuple, list[Comprovante]]:
        """Indexa comprovantes por (data, valor_total) para lookup O(1)."""
        idx: dict[tuple, list[Comprovante]] = {}
        for c in comprovantes:
            key = (c.date, c.amount_total)
            idx.setdefault(key, []).append(c)
        return idx

    def _find_comprovante(
        self,
        tx: Transaction,
        idx: dict,
    ) -> Optional[tuple[Comprovante, int]]:
        """
        Busca o melhor comprovante para a transação.
        Retorna (comprovante, score) ou None se nenhum candidato for encontrado.
        """
        candidates: list[tuple[int, Comprovante]] = []

        for delta in (0, 1, -1, 2, -2):
            lookup_date = tx.date + timedelta(days=delta)
            key = (lookup_date, tx.amount)
            for comp in idx.get(key, []):
                score = 40  # valor exato
                score += 30 if delta == 0 else (15 if abs(delta) == 1 else 5)
                candidates.append((score, comp))

        if not candidates:
            return None

        # Retorna o de maior score (desempate: mais próximo em data)
        candidates.sort(key=lambda x: -x[0])
        best_score, best_comp = candidates[0]
        return best_comp, best_score

    def _resolve_accounts_from_comprovante(
        self, tx: Transaction, comp: Comprovante
    ) -> tuple[Optional[str], Optional[str], str]:
        """
        Resolve COD_DEB e COD_CRED usando o CNPJ do comprovante e o plano de contas.
        Retorna (cod_deb, cod_cred, historico).
        """
        conta = self._plano.by_cnpj(comp.cnpj_beneficiary)
        banco = self._config.cod_banco_principal
        hist = f"{tx.raw_description[:20]} {comp.beneficiary_name[:18]}".strip()[:40]

        if tx.is_debit:
            # Pagamento: débita fornecedor, credita banco
            cod_deb = conta.cod_reduzido if conta else None
            cod_cred = banco
        else:
            # Recebimento: débita banco, credita cliente
            cod_deb = banco
            cod_cred = conta.cod_reduzido if conta else None

        return cod_deb, cod_cred, hist

    def _match_single(
        self, tx: Transaction, comp_idx: dict
    ) -> MatchResult:
        # Camada 0: regras por palavra-chave
        rule = self._rules.match(tx)
        if rule:
            return MatchResult(
                transaction=tx,
                matched_comprovante=None,
                cod_deb=rule.cod_deb,
                cod_cred=rule.cod_cred,
                historico=rule.historico,
                score=95,
                match_type='keyword',
                needs_review=False,
            )

        # Camada 1: match por comprovante
        comp_result = self._find_comprovante(tx, comp_idx)
        if comp_result:
            comp, score = comp_result
            cod_deb, cod_cred, hist = self._resolve_accounts_from_comprovante(tx, comp)

            if cod_deb and cod_cred:
                # CNPJ encontrado no plano de contas
                score += 20
                return MatchResult(
                    transaction=tx,
                    matched_comprovante=comp,
                    cod_deb=cod_deb,
                    cod_cred=cod_cred,
                    historico=hist,
                    score=min(score, 100),
                    match_type='comprovante',
                    needs_review=False,
                )
            else:
                # Comprovante encontrado mas CNPJ não está no plano de contas → revisão
                missing_side = "débito" if not cod_deb else "crédito"
                return MatchResult(
                    transaction=tx,
                    matched_comprovante=comp,
                    cod_deb=cod_deb,
                    cod_cred=cod_cred,
                    historico=hist,
                    score=score,
                    match_type='comprovante_parcial',
                    needs_review=True,
                    review_reason=f"CNPJ {comp.cnpj_beneficiary} não encontrado no plano de contas (conta de {missing_side})",
                )

        # Camada 1b: CNPJ na descrição (PIX RECEBIDO/ENVIADO, CR COB, TED)
        cnpj_result = self._match_by_description_cnpj(tx)
        if cnpj_result:
            return cnpj_result

        # Camada 3: sem match → revisão humana
        return MatchResult(
            transaction=tx,
            matched_comprovante=None,
            cod_deb=None,
            cod_cred=None,
            historico=tx.raw_description[:40],
            score=0,
            match_type='unmatched',
            needs_review=True,
            review_reason='Sem comprovante ou regra correspondente',
        )

    # ------------------------------------------------------------------
    # Camada 1b helpers
    # ------------------------------------------------------------------

    _CNPJ_IN_DESC = __import__('re').compile(r'\b(\d{11,14})\b')

    def _match_by_description_cnpj(self, tx: Transaction) -> Optional[MatchResult]:
        """
        Camada 1b: extrai CPF/CNPJ da descrição da transação e faz lookup no plano.
        Cobre principalmente PIX RECEBIDO (68% das transações).
        Usa conta genérica como fallback se CNPJ não estiver no plano.
        """
        desc = tx.raw_description.upper()
        banco = self._config.cod_banco_principal

        # PIX RECEBIDO — sempre crédito para a empresa
        if 'PIX RECEBIDO' in desc or 'CR COB' in desc or 'A CR COB' in desc:
            cnpj = self._extract_cnpj_from_description(tx.raw_description)
            conta = self._plano.by_cnpj(cnpj) if cnpj else None
            cod_cred = conta.cod_reduzido if conta else self._config.cod_receita_pix
            hist = f"{tx.raw_description[:30]} {cnpj or ''}".strip()[:40]
            return MatchResult(
                transaction=tx,
                matched_comprovante=None,
                cod_deb=banco,
                cod_cred=cod_cred,
                historico=hist,
                score=80 if conta else 60,
                match_type='cnpj_desc' if conta else 'generic_rule',
                needs_review=False,
            )

        # TED RECEBIDA
        if 'TED RECEBIDA' in desc:
            cod_cred = self._config.cod_receita_pix
            return MatchResult(
                transaction=tx,
                matched_comprovante=None,
                cod_deb=banco,
                cod_cred=cod_cred,
                historico=tx.raw_description[:40],
                score=55,
                match_type='generic_rule',
                needs_review=False,
            )

        # PIX ENVIADO sem comprovante → conta genérica + flag de revisão leve
        if 'PIX ENVIADO' in desc or 'TED ENVIADA' in desc:
            cnpj = self._extract_cnpj_from_description(tx.raw_description)
            conta = self._plano.by_cnpj(cnpj) if cnpj else None
            cod_deb = conta.cod_reduzido if conta else self._config.cod_despesa_pix
            hist = (f"{tx.raw_description[:20]} {tx.beneficiary or ''}").strip()[:40]
            return MatchResult(
                transaction=tx,
                matched_comprovante=None,
                cod_deb=cod_deb,
                cod_cred=banco,
                historico=hist,
                score=70 if conta else 45,
                match_type='cnpj_desc' if conta else 'generic_rule',
                needs_review=(conta is None),
                review_reason=None if conta else 'PIX/TED enviado sem comprovante — confirmar conta',
            )

        # DÉBITO PAGAMENTO DE SALARIO
        if 'PAGAMENTO DE SALARIO' in desc or 'SALARIO' in desc:
            return MatchResult(
                transaction=tx,
                matched_comprovante=None,
                cod_deb=self._config.cod_tarifas,  # usa tarifa como placeholder
                cod_cred=banco,
                historico=tx.raw_description[:40],
                score=50,
                match_type='generic_rule',
                needs_review=True,
                review_reason='Salário: confirmar conta de folha de pagamento',
            )

        return None

    @staticmethod
    def _extract_cnpj_from_description(desc: str) -> Optional[str]:
        """Extrai CPF (11 dígitos) ou CNPJ (14 dígitos) do campo de descrição."""
        import re
        m = re.search(r'\b(\d{11,14})\b', desc)
        return m.group(1) if m else None

    def summary(self, results: list[MatchResult]) -> dict:
        """Retorna estatísticas do processo de matching."""
        total = len(results)
        by_type: dict[str, int] = {}
        for r in results:
            by_type[r.match_type] = by_type.get(r.match_type, 0) + 1

        auto = sum(1 for r in results if not r.needs_review)
        review = total - auto

        return {
            'total': total,
            'auto_matched': auto,
            'needs_review': review,
            'auto_rate': round(auto / total * 100, 1) if total else 0,
            'by_type': by_type,
        }
