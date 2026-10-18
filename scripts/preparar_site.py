#!/usr/bin/env python3
"""Monta um pacote Pages por allowlist e libera somente datas alcançadas da simulação."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from distribuir_meses import FONTE, distribuir

RAIZ = Path(__file__).resolve().parents[1]


def preparar(destino: Path, data_limite: str | None = None, teste_publicacao: bool = False) -> dict:
    hoje = data_limite or datetime.now(timezone(timedelta(hours=-4))).date().isoformat()
    dados = json.loads((RAIZ / 'data/indicadores.json').read_text(encoding='utf-8'))
    calendario = json.loads((RAIZ / 'data/calendario_simulado.json').read_text(encoding='utf-8'))
    dados['mensais'] = distribuir(dados['historico'])
    dados['fonte_ponderacao_mensal'] = FONTE
    dados['simulados'] = [linha for linha in calendario if linha['data'] <= hoje]
    if teste_publicacao:
        # Cópia isolada: não antecipa nem altera o calendário da campanha.
        amostra = dict(calendario[0])
        amostra.update(data=hoje, origem='SIMULADO', teste_publicacao=True)
        dados['simulados'] = [amostra]
    dados['teste_publicacao'] = teste_publicacao
    dados['publicado_em'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    dados['data_limite_simulacao'] = hoje
    permitidos = {'index.html', 'metodologia.html', 'assets', 'data', '.nojekyll'}
    if destino.exists():
        inesperados = {item.name for item in destino.iterdir()} - permitidos
        if inesperados:
            raise ValueError(f'Arquivos inesperados no pacote: {sorted(inesperados)}')
        arquivos_permitidos = {
            'index.html', 'metodologia.html', 'assets/app.js', 'assets/styles.css',
            'data/indicadores.json', '.nojekyll',
                        'assets/fonts/sora/sora-latin.woff2', 'assets/fonts/sora/sora-latin-ext.woff2',
        }
        for arquivo in destino.rglob('*'):
            if arquivo.is_file() and arquivo.relative_to(destino).as_posix() not in arquivos_permitidos:
                raise ValueError(f'Arquivo não permitido: {arquivo.relative_to(destino)}')
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RAIZ / 'index.html', destino / 'index.html')
    shutil.copy2(RAIZ / 'metodologia.html', destino / 'metodologia.html')
    shutil.copytree(RAIZ / 'assets', destino / 'assets', dirs_exist_ok=True)
    (destino / 'data').mkdir(exist_ok=True)
    (destino / 'data/indicadores.json').write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    (destino / '.nojekyll').touch()
    return dados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path, default=RAIZ / 'dist')
    parser.add_argument('--teste-publicacao', action='store_true', help='Publica apenas uma amostra sintética isolada para teste de deploy.')
    args = parser.parse_args()
    dados = preparar(args.destino, teste_publicacao=args.teste_publicacao)
    print(f"Site preparado. Simulação: {len(dados['simulados'])} agregados publicados.")


if __name__ == '__main__':
    main()
