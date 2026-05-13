"""
Interface para o Plano de Contas do Domínio Sistemas.

Hierarquia de fontes:
  1. SQL Server (Domínio) — fonte autoritativa, via pyodbc
  2. JSON cache local — gerado pela extração do XLS do Domínio via win32com
  3. Fixture stub — para testes unitários

O código reduzido (ex: "1843", "374") é o identificador usado nos lançamentos de importação.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ContaEntry:
    cod_reduzido: str
    nome: str
    natureza: str            # "D" débito / "C" crédito
    cnpj: Optional[str] = None
    classif: str = ""        # classificação hierárquica ex: "1.1.1.02.002"


def _normalize_name(s: str) -> str:
    """Remove sufixos jurídicos e pontuação para fuzzy matching."""
    s = s.upper()
    for suffix in (' LTDA', ' S/A', ' S.A.', ' S.A', ' EIRELI', ' ME', ' EPP',
                   ' INDUSTRIA', ' IND.', ' IND ', ' COM.', ' COM ', ' COMERCIO',
                   ' E CIA', ' CIA.', ' LTDA.', ' -'):
        s = s.replace(suffix, '')
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


class PlanoDeContas:
    """
    Repositório de contas analíticas para uma empresa.
    Suporta lookup por código reduzido, CNPJ e fuzzy matching por nome.
    """

    def __init__(self, empresa_cnpj: str):
        self.empresa_cnpj = empresa_cnpj
        self._by_cod: dict[str, ContaEntry] = {}
        self._by_cnpj: dict[str, ContaEntry] = {}
        self._by_nome_norm: dict[str, ContaEntry] = {}  # nome normalizado → conta

    def add(self, entry: ContaEntry) -> None:
        self._by_cod[entry.cod_reduzido] = entry
        if entry.cnpj:
            self._by_cnpj[entry.cnpj] = entry
        self._by_nome_norm[_normalize_name(entry.nome)] = entry

    def by_cod(self, cod: str) -> Optional[ContaEntry]:
        return self._by_cod.get(str(cod))

    def by_cnpj(self, cnpj: str) -> Optional[ContaEntry]:
        return self._by_cnpj.get(cnpj)

    def by_name_fuzzy(self, name: str, min_score: int = 75) -> Optional[ContaEntry]:
        """
        Busca conta pelo nome usando rapidfuzz token_sort_ratio.
        Retorna a conta com maior score se >= min_score, ou None.
        """
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None

        query = _normalize_name(name)
        if not query:
            return None

        choices = list(self._by_nome_norm.keys())
        result = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= min_score:
            return self._by_nome_norm[result[0]]
        return None

    def enrich_cnpj(self, cnpj: str, name: str, min_score: int = 75) -> Optional[ContaEntry]:
        """
        Tenta associar um CNPJ a uma conta existente via fuzzy matching.
        Se encontrar, registra o CNPJ na conta para lookups futuros.
        """
        # Já temos o CNPJ mapeado?
        conta = self.by_cnpj(cnpj)
        if conta:
            return conta

        # Tenta pelo nome
        conta = self.by_name_fuzzy(name, min_score)
        if conta:
            conta.cnpj = cnpj
            self._by_cnpj[cnpj] = conta
            return conta

        return None

    def all_cods(self) -> list[str]:
        return list(self._by_cod.keys())

    @classmethod
    def from_json(cls, path: str | Path) -> "PlanoDeContas":
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        pdc = cls(empresa_cnpj=data['empresa_cnpj'])
        for item in data['contas']:
            if item.get('sintetica'):
                continue  # só analíticas
            pdc.add(ContaEntry(
                cod_reduzido=str(item['cod_reduzido']),
                nome=item['nome'],
                natureza=item.get('natureza', 'D'),
                cnpj=item.get('cnpj'),
                classif=item.get('classif', ''),
            ))
        return pdc

    def to_json(self, path: str | Path) -> None:
        data = {
            'empresa_cnpj': self.empresa_cnpj,
            'contas': [
                {'cod_reduzido': e.cod_reduzido, 'nome': e.nome,
                 'natureza': e.natureza, 'cnpj': e.cnpj}
                for e in self._by_cod.values()
            ],
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def from_dominio_sql(cls, empresa_cnpj: str, connection_string: str) -> "PlanoDeContas":
        import pyodbc
        pdc = cls(empresa_cnpj=empresa_cnpj)
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.CodReduzido, c.Nome, c.Natureza,
                   ISNULL(f.CNPJ, '') as CNPJ
            FROM PlanoContas c
            LEFT JOIN Fornecedores f ON f.CodConta = c.CodReduzido
            WHERE c.EmpresaCNPJ = ? AND c.Sintetica = 0
            ORDER BY c.CodReduzido
            """,
            empresa_cnpj,
        )
        for row in cursor.fetchall():
            pdc.add(ContaEntry(
                cod_reduzido=str(row.CodReduzido),
                nome=row.Nome,
                natureza=row.Natureza or 'D',
                cnpj=re.sub(r'[^\d]', '', row.CNPJ) or None,
            ))
        conn.close()
        return pdc

    @classmethod
    def stub(cls, empresa_cnpj: str = '00000000000000') -> "PlanoDeContas":
        pdc = cls(empresa_cnpj=empresa_cnpj)
        for cod, nome, nat in [
            ('1843', 'BANCO SANTANDER CC 13.000641-6', 'D'),
            ('11',   'SANTANDER CONTAMAX EMPRESARIAL', 'D'),
            ('8',    'BANCO SICOOB OURO VERDE',         'D'),
            ('1831', 'BANCO DO BRASIL',                 'D'),
            ('374',  'DESPESAS BANCARIAS',              'D'),
            ('350',  'IMPOSTOS E TAXAS DIVERSAS',       'D'),
            ('368',  'JUROS PASSIVOS',                  'D'),
            ('504',  'DUPLICATAS A RECEBER',            'C'),
            ('187',  'SALARIOS E ORDENADOS A PAGAR',    'C'),
            ('354',  'ENERGIA ELETRICA',                'D'),
            ('355',  'AGUA E ESGOTO',                   'D'),
            ('356',  'TELEFONE/INTERNET',               'D'),
            ('165',  'FORNECEDORES',                    'C'),
            ('172',  'ICMS A RECOLHER',                 'C'),
            ('432',  'RECEITAS DE APLICACOES FINANCEIRAS', 'C'),
        ]:
            pdc.add(ContaEntry(cod, nome, nat))
        return pdc
