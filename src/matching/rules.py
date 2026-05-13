"""
Camada 0 do motor de matching: regras determinísticas por palavra-chave.

Cobertura no extrato Santander ALO EMBALAGENS (com config real):
  - CONTAMAX aplicação + resgate
  - Tarifas bancárias (DESPESAS BANCARIAS)
  - IOF (IMPOSTOS E TAXAS DIVERSAS)
  - GETNET (recebimento cartão → DUPLICATAS A RECEBER)
  - Débitos automáticos: água, telefone, energia
  - DARFs, ICMS
  - Salários
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..models import Transaction


@dataclass
class RuleMatch:
    cod_deb: str
    cod_cred: str
    historico: str
    rule_name: str


@dataclass
class EmpresaConfig:
    empresa_cnpj: str
    cod_banco_principal: str
    cod_contamax: str
    cod_tarifas: str
    cod_iof: str
    cod_receita_cartao: str
    cod_receita_pix: str
    cod_despesa_pix: str
    cod_debito_automatico: str
    cod_darf: str
    cod_tributo_estadual: str
    # campos extras com default para compatibilidade com stub
    cod_energia: str = ''
    cod_agua: str = ''
    cod_telefone: str = ''
    cod_salario: str = ''
    cod_juros: str = ''

    @classmethod
    def from_json(cls, path: str | Path) -> "EmpresaConfig":
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return cls(
            empresa_cnpj=d['empresa_cnpj'],
            cod_banco_principal=d['cod_banco_principal'],
            cod_contamax=d['cod_contamax'],
            cod_tarifas=d['cod_tarifas'],
            cod_iof=d['cod_iof'],
            cod_receita_cartao=d['cod_receita_cartao'],
            cod_receita_pix=d['cod_receita_pix'],
            cod_despesa_pix=d['cod_despesa_pix'],
            cod_debito_automatico=d['cod_debito_automatico'],
            cod_darf=d['cod_darf'],
            cod_tributo_estadual=d['cod_tributo_estadual'],
            cod_energia=d.get('cod_energia', ''),
            cod_agua=d.get('cod_agua', ''),
            cod_telefone=d.get('cod_telefone', ''),
            cod_salario=d.get('cod_salario', ''),
            cod_juros=d.get('cod_juros', ''),
        )

    @classmethod
    def stub(cls) -> "EmpresaConfig":
        return cls(
            empresa_cnpj='04744695000177',
            cod_banco_principal='1843',
            cod_contamax='11',
            cod_tarifas='374',
            cod_iof='350',
            cod_receita_cartao='504',
            cod_receita_pix='504',
            cod_despesa_pix='165',
            cod_debito_automatico='51',
            cod_darf='350',
            cod_tributo_estadual='172',
            cod_energia='354',
            cod_agua='355',
            cod_telefone='356',
            cod_salario='187',
            cod_juros='368',
        )


class RuleSet:
    def __init__(self, config: EmpresaConfig):
        self._c = config
        self._rules = self._build_rules()

    def match(self, tx: Transaction) -> Optional[RuleMatch]:
        desc = tx.raw_description.upper()
        ben = (tx.beneficiary or '').upper()
        for rule in self._rules:
            r = rule(tx, desc, ben)
            if r:
                return r
        return None

    def _build_rules(self) -> list:
        c = self._c

        def contamax_aplicacao(tx, desc, ben):
            if 'APLICACAO CONTAMAX' in desc:
                return RuleMatch(c.cod_contamax, c.cod_banco_principal,
                                 'APLICACAO CONTAMAX', 'contamax_aplicacao')

        def contamax_resgate(tx, desc, ben):
            if 'RESGATE CONTAMAX' in desc:
                return RuleMatch(c.cod_banco_principal, c.cod_contamax,
                                 'RESGATE CONTAMAX AUTOMATICO', 'contamax_resgate')

        def tarifa(tx, desc, ben):
            kws = ['TARIFA AVULSA', 'TARIFA MANUTENCAO', 'TAR LIQ COB',
                   'TARIFA COBR', 'MANUTENCAO DE CONTA', 'TARIFA PACOTE']
            if any(k in desc for k in kws):
                return RuleMatch(c.cod_tarifas, c.cod_banco_principal,
                                 tx.raw_description[:40], 'tarifa')

        def iof(tx, desc, ben):
            if 'IOF IMPOSTO' in desc or 'IOF ADICIONAL' in desc:
                return RuleMatch(c.cod_iof, c.cod_banco_principal,
                                 tx.raw_description[:40], 'iof')

        def getnet(tx, desc, ben):
            if 'GETNET' in ben or 'PAGAMENTO CARTAO DE DEBITO' in desc or 'PAGAMENTO CARTAO DE CREDITO' in desc:
                hist = f"{tx.raw_description} {tx.beneficiary or ''}".strip()[:40]
                return RuleMatch(c.cod_banco_principal, c.cod_receita_cartao, hist, 'getnet')

        def transf_interna(tx, desc, ben):
            if 'TRANSF VALORES MESMA TITULARIDADE' in desc:
                if tx.is_debit:
                    return RuleMatch(c.cod_tarifas, c.cod_banco_principal,
                                     'TRANSF TITULARIDADE', 'transf_interna')
                else:
                    return RuleMatch(c.cod_banco_principal, c.cod_receita_pix,
                                     'TRANSF TITULARIDADE', 'transf_interna')

        def darf(tx, desc, ben):
            if 'PAGAMENTO DARF' in desc or 'PAGAMENTO DARJ' in desc:
                return RuleMatch(c.cod_darf, c.cod_banco_principal,
                                 tx.raw_description[:40], 'darf')

        def tributo_estadual(tx, desc, ben):
            if 'PGTO TRIBUTO ESTADUAL' in desc or 'TRIBUTO ESTADUAL' in desc:
                return RuleMatch(c.cod_tributo_estadual, c.cod_banco_principal,
                                 tx.raw_description[:40], 'tributo_estadual')

        def debito_agua(tx, desc, ben):
            # SANEPAR aparece no beneficiary como "SANEPAR"
            if ('DEBITO AUT. CONTA AGUA' in desc or
                    'AGUA' in desc and 'DEBITO AUT' in desc or
                    'SANEPAR' in ben.upper()):
                cod = c.cod_agua if c.cod_agua else c.cod_debito_automatico
                hist = f"{tx.raw_description[:20]} {tx.beneficiary or ''}".strip()[:40]
                return RuleMatch(cod, c.cod_banco_principal, hist, 'debito_agua')

        def debito_telefone(tx, desc, ben):
            if 'PGTO CONTA DE TELEFONE' in desc or 'TELEFONE' in desc and 'PGTO' in desc:
                cod = c.cod_telefone if c.cod_telefone else c.cod_debito_automatico
                hist = f"{tx.raw_description[:20]} {tx.beneficiary or ''}".strip()[:40]
                return RuleMatch(cod, c.cod_banco_principal, hist, 'debito_telefone')

        def debito_energia(tx, desc, ben):
            if 'ENERGIA' in desc and ('DEBITO AUT' in desc or 'PGTO' in desc):
                cod = c.cod_energia if c.cod_energia else c.cod_debito_automatico
                hist = f"{tx.raw_description[:20]} {tx.beneficiary or ''}".strip()[:40]
                return RuleMatch(cod, c.cod_banco_principal, hist, 'debito_energia')

        def salario(tx, desc, ben):
            if 'PAGAMENTO DE SALARIO' in desc or 'DEBITO PAGAMENTO DE SALARIO' in desc:
                cod = c.cod_salario if c.cod_salario else c.cod_debito_automatico
                return RuleMatch(cod, c.cod_banco_principal,
                                 'PAGAMENTO SALARIOS', 'salario')

        return [
            contamax_aplicacao, contamax_resgate,
            tarifa, iof, getnet, transf_interna,
            darf, tributo_estadual,
            debito_agua, debito_telefone, debito_energia,
            salario,
        ]
