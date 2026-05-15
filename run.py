"""
Lincium — runner principal.

Uso:
  python run.py                         # processa extrato padrão + abre revisão
  python run.py --extrato caminho.pdf   # extrato específico
  python run.py --port 8080             # porta alternativa
  python run.py --no-server             # só gera os arquivos, sem abrir o browser
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))


def run_pipeline(extrato_path: Path) -> int:
    from src.parsers.santander import parse_file
    from src.matching.engine import MatchEngine
    from src.matching.rules import EmpresaConfig
    from src.matching.plano_de_contas import PlanoDeContas
    from src.output.batch import save_batch
    from src.output.dominio import generate

    print(f"[1/4] Lendo extrato: {extrato_path.name}")
    transactions = parse_file(str(extrato_path), year=2026)
    print(f"      {len(transactions)} transações extraídas")

    print("[2/4] Carregando configuração ALO EMBALAGENS")
    cfg = EmpresaConfig.from_json(DATA_DIR / "config_alo_embalagens.json")
    plano = PlanoDeContas.from_json(DATA_DIR / "plano_contas_alo_embalagens.json")

    print("[3/4] Executando motor de matching")
    engine = MatchEngine(cfg, plano)
    results = engine.match_all(transactions, comprovantes=[])
    stats = engine.summary(results)
    print(f"      Auto: {stats['auto_matched']} ({stats['auto_rate']}%)  |  Revisão: {stats['needs_review']}")

    print("[4/4] Salvando batch + arquivo Domínio")
    save_batch(results, OUTPUT_DIR / "batch_latest.json")
    generate(results, cfg.empresa_cnpj, output_path=OUTPUT_DIR / "alo_embalagens_01_2026_importacao.txt")
    print(f"      Salvo em {OUTPUT_DIR}/")

    try:
        from src.db.connection import db_available
        from src.db import repository as db_repo
        if db_available():
            batch_id = db_repo.save_batch(
                results,
                tenant_id=db_repo.PRIME_TENANT_ID,
                client_cnpj=cfg.empresa_cnpj,
                client_name="ALO EMBALAGENS LTDA",
                period_year=2026,
                period_month=1,
            )
            print(f"      PostgreSQL: batch {batch_id[:8]}... salvo")
    except Exception as e:
        print(f"      PostgreSQL indisponível: {e}")

    return stats["needs_review"]


def start_server(port: int):
    import uvicorn
    print(f"\nServidor de revisão em http://localhost:{port}")
    print("Pressione Ctrl+C para parar.\n")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(
        "src.review.app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="warning",
    )


def main():
    parser = argparse.ArgumentParser(description="Lincium — Conciliação Contábil")
    parser.add_argument(
        "--extrato",
        default=str(ROOT.parent / "prime-grupo/PRIME/setor-contabil/docs-brutos/Docs Testes/SANTANDER 01.2026 - MATRIZ.pdf"),
        help="Caminho do PDF de extrato bancário",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-server", action="store_true", help="Só gera os arquivos, sem servidor")
    args = parser.parse_args()

    extrato = Path(args.extrato)
    if not extrato.exists():
        print(f"Arquivo não encontrado: {extrato}")
        sys.exit(1)

    needs_review = run_pipeline(extrato)

    if args.no_server:
        print("\nPronto. Arquivo em output/alo_embalagens_01_2026_importacao.txt")
        return

    if needs_review > 0:
        print(f"\n{needs_review} lançamentos precisam de revisão. Abrindo interface...")
        start_server(args.port)
    else:
        print("\nTodos os lançamentos foram classificados automaticamente!")
        print("Arquivo pronto em output/alo_embalagens_01_2026_importacao.txt")


if __name__ == "__main__":
    main()
