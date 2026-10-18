'use strict';

const numero = (valor, casas = 1) => new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: casas, maximumFractionDigits: casas,
}).format(valor);
const porId = (id) => document.getElementById(id);
const somar = (linhas, campo) => linhas.reduce((total, linha) => total + linha[campo], 0);
const periodo = (linha) => `${linha.periodo_inicio.slice(8, 10)}/${linha.periodo_inicio.slice(5, 7)}/${linha.ano} – ${linha.periodo_fim.slice(8, 10)}/${linha.periodo_fim.slice(5, 7)}/${linha.periodo_fim.slice(0, 4)}`;
let dados;
let atualizando = false;

function simuladosDaConsulta() {
  if (porId('filtro-base').value !== 'combinado' || dados.teste_publicacao) return [];
  return dados.simulados.map((linha) => ({...linha, ano: linha.data.slice(0, 4), periodo_inicio: linha.data, periodo_fim: linha.data}));
}

async function obterDados() {
  const resposta = await fetch(`data/indicadores.json?atualizacao=${Date.now()}`, {cache: 'no-store'});
  if (!resposta.ok) throw new Error('Falha ao obter indicadores');
  return resposta.json();
}

async function consultarAtualizacoes() {
  if (atualizando || document.hidden) return;
  atualizando = true;
  try {
    const novos = await obterDados();
    if (novos.publicado_em !== dados.publicado_em) {
      dados = novos;
      atualizar();
    }
    porId('erro-dados').hidden = true;
  } catch (erro) {
    porId('ultima-atualizacao').textContent = 'Falha ao verificar atualizações. Dados anteriores mantidos; nova tentativa em um minuto.';
  } finally {
    atualizando = false;
  }
}

function opcoes(select, valores, primeira) {
  select.replaceChildren(new Option(primeira, 'todas'));
  [...new Set(valores)].sort().forEach((valor) => select.add(new Option(valor, valor)));
}

function linhasFiltradas() {
  return [...dados.historico, ...simuladosDaConsulta()].filter((linha) =>
    (porId('filtro-ano').value === 'todos' || linha.ano === porId('filtro-ano').value) &&
    (porId('filtro-entidade').value === 'todas' || linha.entidade === porId('filtro-entidade').value) &&
    (porId('filtro-unidade').value === 'todas' || linha.unidade === porId('filtro-unidade').value));
}

function agrupar(linhas, chave) {
  const grupos = new Map();
  linhas.forEach((linha) => {
    const nome = chave(linha);
    if (!grupos.has(nome)) grupos.set(nome, {nome, etanol_l: 0, gasolina_equivalente_l: 0, co2e_evitado_kg: 0});
    const grupo = grupos.get(nome);
    ['etanol_l', 'gasolina_equivalente_l', 'co2e_evitado_kg'].forEach((campo) => { grupo[campo] += linha[campo]; });
  });
  return [...grupos.values()];
}

function criarSvg(tag, atributos = {}, texto = '') {
  const elemento = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(atributos).forEach(([chave, valor]) => elemento.setAttribute(chave, valor));
  if (texto) elemento.textContent = texto;
  return elemento;
}

function desenharGrafico() {
  const ano = porId('grafico-ano').value;
  const baseMensal = [...dados.mensais, ...simuladosDaConsulta().map((linha) => ({...linha, mes: Number(linha.data.slice(5, 7))}))];
  const mensais = baseMensal.filter((linha) => String(linha.ano) === ano &&
    (porId('filtro-entidade').value === 'todas' || linha.entidade === porId('filtro-entidade').value) &&
    (porId('filtro-unidade').value === 'todas' || linha.unidade === porId('filtro-unidade').value));
  const nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const grupos = Array.from({length: ano === '2026' ? Math.max(10, ...mensais.map((linha) => linha.mes)) : 12}, (_, indice) => {
    const mes = mensais.filter((linha) => linha.mes === indice + 1);
    return {nome: nomes[indice], etanol_l: somar(mes, 'etanol_l'), co2e_evitado_kg: somar(mes, 'co2e_evitado_kg')};
  });
  porId('chart-total').textContent = `${numero(somar(mensais, 'co2e_evitado_kg') / 1000)} t em ${ano}`;
  porId('chart-note').textContent = ano === '2026'
    ? 'Período: janeiro a 18 de outubro de 2026. Setembro e outubro usam as vendas dos mesmos meses de 2025 como referência; outubro considera 18 dias. Os valores mensais são estimados, não abastecimentos medidos por mês.'
    : 'Rateio dos totais originais pela sazonalidade das vendas estaduais de etanol. Não representa medição mensal da frota.';
  if (porId('filtro-base').value === 'combinado') porId('chart-note').textContent += ' Inclui incrementos SIMULADOS publicados, separados na fonte do histórico.';
  porId('monthly-body').replaceChildren();
  if (!mensais.length) {
    porId('chart-total').textContent = `Sem dados em ${ano}`;
    porId('chart-periodos').textContent = 'Não há dados para este ano, entidade e unidade.';
    porId('chart-periodos').setAttribute('aria-label', 'Sem dados no recorte selecionado.');
    adicionarLinha(porId('monthly-body'), ['Sem dados neste recorte', '—', '—']);
    return;
  }
  grupos.forEach((grupo) => adicionarLinha(porId('monthly-body'), [grupo.nome, numero(grupo.etanol_l), numero(grupo.co2e_evitado_kg / 1000, 3)]));
  const svg = criarSvg('svg', {viewBox: '0 0 700 330', 'aria-hidden': 'true'});
  const maximo = Math.max(...grupos.map((g) => g.co2e_evitado_kg / 1000), 1) * 1.18;
  const largura = 600 / Math.max(grupos.length, 1);
  for (let i = 0; i <= 4; i += 1) {
    const y = 260 - i * 58;
    svg.append(criarSvg('line', {x1: 60, x2: 680, y1: y, y2: y, class: 'grid'}));
    svg.append(criarSvg('text', {x: 48, y: y + 4, 'text-anchor': 'end'}, numero(maximo * i / 4, 0)));
  }
  svg.append(criarSvg('text', {x: 60, y: 15}, 't CO₂e direto evitado'));
  grupos.forEach((grupo, indice) => {
    const altura = grupo.co2e_evitado_kg / 1000 / maximo * 232;
    const x = 70 + indice * largura;
    const barra = criarSvg('rect', {x, y: 260 - altura, width: Math.min(largura * 0.65, 110), height: altura, class: 'bar'});
    barra.append(criarSvg('title', {}, `${grupo.nome}: ${numero(grupo.co2e_evitado_kg / 1000)} t CO₂e`));
    svg.append(barra);
    svg.append(criarSvg('text', {x: x + Math.min(largura * 0.65, 110) / 2, y: 250 - altura, 'text-anchor': 'middle'}, numero(grupo.co2e_evitado_kg / 1000)));
    const partes = grupo.nome.split(' – ');
    partes.forEach((parte, linha) => svg.append(criarSvg('text', {x: x + Math.min(largura * 0.65, 110) / 2, y: 282 + linha * 16, 'text-anchor': 'middle'}, parte)));
  });
  porId('chart-periodos').replaceChildren(svg);
  porId('chart-periodos').setAttribute('aria-label', grupos.length ? `Distribuição mensal estimada de CO₂e direto evitado em ${ano}, ${grupos.length} meses. Valores disponíveis na tabela mensal.` : 'Nenhum dado no recorte selecionado.');
}

function desenharEntidades(linhas) {
  const grupos = agrupar(linhas, (linha) => linha.entidade).sort((a, b) => a.nome.localeCompare(b.nome));
  const maximo = Math.max(...grupos.map((g) => g.co2e_evitado_kg), 1);
  porId('entity-bars').replaceChildren();
  if (!linhas.length) porId('entity-bars').textContent = 'Sem dados neste recorte.';
  grupos.forEach((grupo) => {
    const linha = document.createElement('div');
    linha.className = 'entity-row';
    const nome = document.createElement('strong');
    nome.textContent = grupo.nome;
    const trilho = document.createElement('div');
    trilho.className = 'entity-track';
    trilho.setAttribute('aria-hidden', 'true');
    const preenchimento = document.createElement('div');
    preenchimento.className = 'entity-fill';
    preenchimento.style.width = `${grupo.co2e_evitado_kg / maximo * 100}%`;
    trilho.append(preenchimento);
    const valor = document.createElement('span');
    valor.className = 'entity-value';
    valor.textContent = `${numero(grupo.co2e_evitado_kg / 1000)} t`;
    linha.append(nome, trilho, valor);
    porId('entity-bars').append(linha);
  });
}

function atualizarTabela(linhas) {
  const grupos = new Map();
  linhas.forEach((linha) => {
    const chave = `${linha.ano}|${linha.entidade}`;
    if (!grupos.has(chave)) grupos.set(chave, {...linha, etanol_l: 0, gasolina_equivalente_l: 0, co2e_evitado_kg: 0});
    const grupo = grupos.get(chave);
    grupo.periodo_inicio = grupo.periodo_inicio < linha.periodo_inicio ? grupo.periodo_inicio : linha.periodo_inicio;
    grupo.periodo_fim = grupo.periodo_fim > linha.periodo_fim ? grupo.periodo_fim : linha.periodo_fim;
    ['etanol_l', 'gasolina_equivalente_l', 'co2e_evitado_kg'].forEach((campo) => { grupo[campo] += linha[campo]; });
  });
  porId('table-body').replaceChildren();
  grupos.forEach((grupo) => {
    const tr = document.createElement('tr');
    [periodo(grupo), grupo.entidade, numero(grupo.etanol_l), numero(grupo.gasolina_equivalente_l), numero(grupo.co2e_evitado_kg / 1000, 3)].forEach((valor) => {
      const td = document.createElement('td');
      td.textContent = valor;
      tr.append(td);
    });
    porId('table-body').append(tr);
  });
}

function adicionarLinha(corpo, valores) {
  const tr = document.createElement('tr');
  valores.forEach((valor) => {
    const td = document.createElement('td');
    td.textContent = valor;
    tr.append(td);
  });
  corpo.append(tr);
}

function atualizarDiarios() {
  const linhas = dados.simulados.filter((linha) =>
    (porId('filtro-ano').value === 'todos' || linha.data.startsWith(porId('filtro-ano').value)) &&
    (porId('filtro-entidade').value === 'todas' || linha.entidade === porId('filtro-entidade').value) &&
    (porId('filtro-unidade').value === 'todas' || linha.unidade === porId('filtro-unidade').value));
  porId('daily-body').replaceChildren();
  const grupos = agrupar(linhas, (linha) => `${linha.data}|${linha.entidade}`).sort((a, b) => b.nome.localeCompare(a.nome));
  grupos.forEach((grupo) => {
    const [data, entidade] = grupo.nome.split('|');
    adicionarLinha(porId('daily-body'), [data.split('-').reverse().join('/'), entidade, numero(grupo.etanol_l), numero(grupo.co2e_evitado_kg / 1000, 3), dados.teste_publicacao ? 'SIMULADO · TESTE' : 'SIMULADO']);
  });
  porId('simulation-state').textContent = linhas.length
    ? `${numero(somar(linhas, 'etanol_l'))} L de etanol · ${numero(somar(linhas, 'co2e_evitado_kg') / 1000, 3)} t CO₂e direto evitado (${dados.teste_publicacao ? 'teste de publicação; fora da campanha' : 'simulação'})`
    : 'Nenhum registro publicado no recorte selecionado';
}

function atualizar() {
  const linhas = linhasFiltradas();
  porId('kpi-etanol').textContent = numero(somar(linhas, 'etanol_l'), 0);
  porId('kpi-evitado').textContent = `${numero(somar(linhas, 'co2e_evitado_kg') / 1000)} t`;
  porId('kpi-gasolina').textContent = numero(somar(linhas, 'gasolina_equivalente_l'), 0);
  porId('kpi-real').textContent = numero(somar(linhas, 'co2e_real_kg') / 1000, 2);
  desenharGrafico();
  desenharEntidades(linhas);
  atualizarTabela(linhas);
  atualizarDiarios();
  porId('ultima-atualizacao').textContent = `Publicado em ${new Date(dados.publicado_em || dados.gerado_em).toLocaleString('pt-BR', {timeZone: 'America/Campo_Grande'})} · consulta automática a cada minuto`;
  if (porId('filtro-base').value === 'combinado') porId('kpi-real').textContent = '—';
  porId('consulta-status').textContent = linhas.length ? `Consulta atualizada: ${linhas.length} registros agregados no recorte.` : 'Sem dados históricos neste recorte.';
  if (porId('filtro-base').value === 'combinado') porId('consulta-status').textContent += ' Base: histórico + SIMULAÇÃO. Emissão realizada não consolidada: métrica ausente no calendário.';
  if (!linhas.length) {
    ['kpi-etanol', 'kpi-evitado', 'kpi-gasolina', 'kpi-real'].forEach((id) => { porId(id).textContent = '—'; });
    adicionarLinha(porId('table-body'), ['Sem dados neste recorte', '—', '—', '—', '—']);
  }
}

async function iniciar() {
  try {
    dados = await obterDados();
    [...new Set(dados.historico.map((linha) => linha.ano))].sort().forEach((ano) => porId('filtro-ano').add(new Option(ano, ano)));
    opcoes(porId('filtro-entidade'), dados.historico.map((linha) => linha.entidade), 'Todas as entidades');
    opcoes(porId('filtro-unidade'), dados.historico.map((linha) => linha.unidade), 'Todas as unidades');
    porId('filtro-entidade').addEventListener('change', () => {
      const linhas = dados.historico.filter((linha) => porId('filtro-entidade').value === 'todas' || linha.entidade === porId('filtro-entidade').value);
      opcoes(porId('filtro-unidade'), linhas.map((linha) => linha.unidade), 'Todas as unidades');
      atualizar();
    });
    ['filtro-ano', 'filtro-unidade', 'filtro-base'].forEach((id) => porId(id).addEventListener('change', atualizar));
    porId('grafico-ano').addEventListener('change', () => desenharGrafico());
    porId('filtro-ano').addEventListener('change', () => {
      if (porId('filtro-ano').value !== 'todos') porId('grafico-ano').value = porId('filtro-ano').value;
      desenharGrafico();
    });
    porId('limpar-filtros').addEventListener('click', () => {
      porId('filtro-base').value = 'historico';
      porId('filtro-ano').value = 'todos';
      porId('grafico-ano').value = '2026';
      porId('filtro-entidade').value = 'todas';
      opcoes(porId('filtro-unidade'), dados.historico.map((linha) => linha.unidade), 'Todas as unidades');
      atualizar();
    });
    porId('cobertura').textContent = `${numero(dados.cobertura_pbe_percentual, 2)}% do volume`;
    porId('versao-metodologia').textContent = `${dados.metodologia.versao} · GWP100 AR5`;
    const sensibilidade = document.createElement('p');
    sensibilidade.className = 'sensitivity-note';
    sensibilidade.textContent = `Sensibilidade do histórico completo: ${numero(dados.cenarios.find((c) => c.cenario === 'MINIMO').co2e_evitado_kg / 1000)}–${numero(dados.cenarios.find((c) => c.cenario === 'MAXIMO').co2e_evitado_kg / 1000)} t CO₂e. Não é intervalo estatístico de confiança e não acompanha os filtros.`;
    document.querySelector('.context-panel').append(sensibilidade);
    porId('ultima-atualizacao').textContent = `Dados preparados em ${new Intl.DateTimeFormat('pt-BR', {dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Campo_Grande'}).format(new Date(dados.publicado_em || dados.gerado_em))}`;

    atualizar();
    setInterval(consultarAtualizacoes, 60000);
    document.addEventListener('visibilitychange', consultarAtualizacoes);
  } catch (erro) {
    porId('erro-dados').hidden = false;
    porId('ultima-atualizacao').textContent = 'Indicadores temporariamente indisponíveis';
    console.error(erro);
  }
}

iniciar();
