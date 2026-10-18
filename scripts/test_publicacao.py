import json
from html.parser import HTMLParser
import tempfile
import unittest
from pathlib import Path

from preparar_site import RAIZ, preparar
from distribuir_meses import CAMPOS, distribuir


class EstruturaHTML(HTMLParser):
    VAZIOS = {'meta', 'link', 'br', 'hr', 'img', 'input', 'wbr', 'source', 'area', 'base', 'col', 'embed', 'param', 'track'}

    def __init__(self):
        super().__init__()
        self.pilha = []
        self.erros = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VAZIOS:
            self.pilha.append(tag)

    def handle_endtag(self, tag):
        if not self.pilha or self.pilha[-1] != tag:
            self.erros.append((self.getpos(), tag))
        else:
            self.pilha.pop()

    def handle_data(self, texto):
        if '<' in texto and 'script' not in self.pilha:
            self.erros.append(('Possível marcação exposta', texto[:80]))


class PublicacaoTest(unittest.TestCase):
    def test_html_sem_tags_corrompidas(self):
        for nome in ['index.html', 'metodologia.html']:
            with self.subTest(pagina=nome):
                parser = EstruturaHTML()
                parser.feed((RAIZ / nome).read_text(encoding='utf-8'))
                self.assertEqual(parser.erros, [])
                self.assertEqual(parser.pilha, [])


    def test_totais_historicos_reconciliados(self):
        dados = json.loads((RAIZ / 'data/indicadores.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(sum(r['etanol_l'] for r in dados['historico']), 419609.1668, places=2)
        self.assertAlmostEqual(sum(r['co2e_evitado_kg'] for r in dados['historico']), 454742.2296, places=2)
        self.assertEqual(dados['metodologia']['versao'], '1.0')

    def test_rateio_preserva_totais_por_registro_e_semestre(self):
        dados = json.loads((RAIZ / 'data/indicadores.json').read_text(encoding='utf-8'))
        for registro in dados['historico']:
            meses = distribuir([registro])
            for campo in CAMPOS:
                self.assertAlmostEqual(sum(m[campo] for m in meses), registro[campo], places=4)
            self.assertTrue(all(m['origem'] == 'ESTIMATIVA_MENSAL' for m in meses))
            self.assertEqual(min(m['mes'] for m in meses), int(registro['periodo_inicio'][5:7]))
            self.assertEqual(max(m['mes'] for m in meses), int(registro['periodo_fim'][5:7]))
        meses = distribuir(dados['historico'])
        for ano, quantidade in [('2024', 12), ('2025', 12), ('2026', 10)]:
            self.assertEqual(len({m['mes'] for m in meses if str(m['ano']) == ano}), quantidade)
        proxies = [m for m in meses if m['ponderador'] == 'PROXY_2025']
        self.assertTrue(proxies)
        self.assertTrue(all(str(m['ano']) == '2026' and m['mes'] in (9, 10) for m in proxies))
        self.assertTrue(all(m['dias_parciais'] for m in proxies if m['mes'] == 10))

    def test_rateio_outubro_parcial(self):
        from distribuir_meses import VENDAS_MS
        registro = dict(ano='2026', entidade='TESTE', unidade='TESTE',
                        periodo_inicio='2026-09-01', periodo_fim='2026-10-18',
                        **{campo: 1000 for campo in CAMPOS})
        setembro, outubro = distribuir([registro])
        peso_set = VENDAS_MS[2025][8]
        peso_out = VENDAS_MS[2025][9] * 18 / 31
        self.assertAlmostEqual(outubro['etanol_l'], 1000 * peso_out / (peso_set + peso_out), places=3)

    def test_campos_publicos_allowlist(self):
        dados = json.loads((RAIZ / 'data/indicadores.json').read_text(encoding='utf-8'))
        permitidos = {'ano', 'periodo_inicio', 'periodo_fim', 'entidade', 'unidade', 'etanol_l', 'gasolina_equivalente_l', 'co2e_referencia_kg', 'co2e_real_kg', 'co2e_evitado_kg'}
        for linha in dados['historico']:
            self.assertEqual(set(linha), permitidos)

    def test_calendario_e_publicacao_incremental(self):
        calendario = json.loads((RAIZ / 'data/calendario_simulado.json').read_text(encoding='utf-8'))
        self.assertTrue(calendario)
        self.assertTrue(all('2026-10-19' <= r['data'] <= '2026-12-18' for r in calendario))
        self.assertTrue(all(r['origem'] == 'SIMULADO' for r in calendario))
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta)
            antes = preparar(destino, '2026-10-18')
            self.assertEqual(antes['simulados'], [])
            self.assertTrue(antes['mensais'])
            self.assertTrue((destino / 'assets/fonts/sora/sora-latin.woff2').exists())
            primeiro = preparar(destino, '2026-10-19')
            self.assertTrue(primeiro['simulados'])
            self.assertTrue(all(r['data'] == '2026-10-19' for r in primeiro['simulados']))
            fim = preparar(destino, '2026-12-18')
            self.assertEqual(len(fim['simulados']), len(calendario))
            self.assertFalse((destino / 'scripts').exists())
            self.assertFalse((destino / 'data/calendario_simulado.json').exists())
            self.assertFalse(list(destino.rglob('*.sqlite3')))


if __name__ == '__main__':
    unittest.main()
