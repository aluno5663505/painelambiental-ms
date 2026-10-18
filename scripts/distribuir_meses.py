"""Rateio visual estimado; não altera o histórico nem seus resultados ambientais."""
from calendar import monthrange
from datetime import date

FONTE = 'https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/vdpb/vendas-derivados-petroleo-e-etanol/vendas-combustiveis-m3-1990-2025.csv'
VENDAS_MS = {
    2024: [30220.434,29050.05,33112.407,32349.39,29945.683,27325.833,28840.871,28939.365,29178.862,32504.115,32313.293,35420.367],
    2025: [31678.887,29228.79,31821.057,30956.579,30086.918,25635.631,27859.932,27979.094,30185.472,31552.267,29188.624,35010.807],
    2026: [29208.006,26861.369,31240.965,32735.146,30108.01,30776.323,34083.49,36688.019],
}
CAMPOS = ['etanol_l','gasolina_equivalente_l','co2e_referencia_kg','co2e_real_kg','co2e_evitado_kg']


def distribuir(historico):
    resultado = []
    for linha in historico:
        inicio, fim = date.fromisoformat(linha['periodo_inicio']), date.fromisoformat(linha['periodo_fim'])
        partes = []
        for mes in range(inicio.month, fim.month + 1):
            dias_mes = monthrange(inicio.year, mes)[1]
            primeiro = max(inicio, date(inicio.year, mes, 1))
            ultimo = min(fim, date(inicio.year, mes, dias_mes))
            dias = (ultimo - primeiro).days + 1
            disponivel = mes <= len(VENDAS_MS[inicio.year])
            venda = VENDAS_MS[inicio.year if disponivel else 2025][mes - 1]
            partes.append((mes, venda * dias / dias_mes, disponivel))
        soma = sum(peso for _, peso, _ in partes)
        alocados = {campo: 0.0 for campo in CAMPOS}
        for indice, (mes, peso, disponivel) in enumerate(partes):
            item = {chave: linha[chave] for chave in ['ano','entidade','unidade']}
            item.update(mes=mes, origem='ESTIMATIVA_MENSAL', ponderador='ANP_MS' if disponivel else 'PROXY_2025', dias_parciais=mes == fim.month and fim.day < monthrange(fim.year, mes)[1])
            for campo in CAMPOS:
                valor = round(linha[campo] - alocados[campo], 4) if indice == len(partes)-1 else round(linha[campo] * peso / soma, 4)
                item[campo] = valor
                alocados[campo] += valor
            resultado.append(item)
    return resultado
