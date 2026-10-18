#!/usr/bin/env python3
"""Exporta somente indicadores agregados e anonimizados para o dashboard público."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_PUBLICO = "1.0"


def arredondar(valor: float | None, casas: int = 4) -> float:
    return round(float(valor or 0), casas)


def consultar(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> list[dict]:
    cursor = conexao.execute(sql, parametros)
    colunas = [item[0] for item in cursor.description]
    return [dict(zip(colunas, linha, strict=True)) for linha in cursor.fetchall()]


def exportar(conexao: sqlite3.Connection) -> dict:
    metodologia = consultar(
        conexao,
        """
        SELECT versao, nome, fronteira, gwp_edicao
        FROM metodologia_emissao WHERE status='ATIVA' ORDER BY id DESC LIMIT 1
        """,
    )[0]

    historico = consultar(
        conexao,
        """
        SELECT substr(r.periodo_inicio, 1, 4) AS ano,
               r.periodo_inicio AS periodo_inicio, r.periodo_fim AS periodo_fim,
               r.entidade, u.nome AS unidade,
               SUM(h.litros_etanol) AS etanol_l,
               SUM(h.litros_gasolina_equivalente) AS gasolina_equivalente_l,
               SUM(h.co2e_referencia_kg) AS co2e_referencia_kg,
               SUM(h.co2e_real_kg) AS co2e_real_kg,
               SUM(h.co2e_evitado_kg) AS co2e_evitado_kg
        FROM resultado_emissao_historica h
        JOIN consumo_historico c ON c.id=h.consumo_historico_id
        JOIN relatorio r ON r.id=c.relatorio_id
        JOIN unidade u ON u.id=c.unidade_id
        JOIN metodologia_emissao m ON m.id=h.metodologia_id
        WHERE h.cenario='CENTRAL' AND m.status='ATIVA'
        GROUP BY ano, r.periodo_inicio, r.periodo_fim, r.entidade, u.nome
        ORDER BY r.periodo_inicio, r.entidade, u.nome
        """,
    )
    for linha in historico:
        for campo in (
            "etanol_l", "gasolina_equivalente_l", "co2e_referencia_kg",
            "co2e_real_kg", "co2e_evitado_kg",
        ):
            linha[campo] = arredondar(linha[campo])

    cenarios = consultar(
        conexao,
        """
        SELECT h.cenario,
               SUM(h.litros_etanol) AS etanol_l,
               SUM(h.litros_gasolina_equivalente) AS gasolina_equivalente_l,
               SUM(h.co2e_evitado_kg) AS co2e_evitado_kg
        FROM resultado_emissao_historica h
        JOIN metodologia_emissao m ON m.id=h.metodologia_id
        WHERE m.status='ATIVA'
        GROUP BY h.cenario ORDER BY CASE h.cenario WHEN 'MINIMO' THEN 1 WHEN 'CENTRAL' THEN 2 ELSE 3 END
        """,
    )
    for linha in cenarios:
        for campo in ("etanol_l", "gasolina_equivalente_l", "co2e_evitado_kg"):
            linha[campo] = arredondar(linha[campo])

    simulados = consultar(
        conexao,
        """
        SELECT e.data_evento AS data, e.entidade, u.nome AS unidade,
               SUM(e.quantidade_litros) AS volume_l,
               SUM(CASE WHEN e.combustivel='ETANOL' THEN e.quantidade_litros ELSE 0 END) AS etanol_l,
               SUM(COALESCE(s.litros_gasolina_equivalente, 0)) AS gasolina_equivalente_l,
               SUM(COALESCE(s.co2e_evitado_kg, 0)) AS co2e_evitado_kg
        FROM evento_consumo_simulado e
        JOIN unidade u ON u.id=e.unidade_id
        LEFT JOIN resultado_emissao_simulada s
          ON s.evento_simulado_id=e.id AND s.cenario='CENTRAL'
        WHERE e.estado='PUBLICADO' AND e.origem='SIMULADO'
        GROUP BY e.data_evento, e.entidade, u.nome
        ORDER BY e.data_evento, e.entidade, u.nome
        """,
    )
    for linha in simulados:
        for campo in ("volume_l", "etanol_l", "gasolina_equivalente_l", "co2e_evitado_kg"):
            linha[campo] = arredondar(linha[campo])

    return {
        "schema": SCHEMA_PUBLICO,
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "aviso": "Dados históricos agregados e dados demonstrativos identificados; nenhum dado pessoal ou placa é publicado.",
        "metodologia": metodologia,
        "cobertura_pbe_percentual": 56.95,
        "historico": historico,
        "cenarios": cenarios,
        "simulados": simulados,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banco", type=Path, required=True)
    parser.add_argument("--saida", type=Path, default=Path("data/indicadores.json"))
    args = parser.parse_args()
    if not args.banco.is_file():
        parser.error(f"banco não encontrado: {args.banco}")
    with sqlite3.connect(f"file:{args.banco.resolve()}?mode=ro", uri=True) as conexao:
        dados = exportar(conexao)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dados públicos exportados: {args.saida}")
    print(f"Histórico: {len(dados['historico'])} agregados; simulação publicada: {len(dados['simulados'])} agregados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
