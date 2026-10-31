/**
 * @fileoverview Aplicação cliente nativa Vanilla JS para o painel executivo Radar 4966.
 * Consome os dados compilados em data/dashboard_data.json e inicializa as visualizações
 * interativas via Chart.js, além do simulador reativo de capital e sensibilidade.
 */

// Formatadores BRL
const formatarMoeda = (valor) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(valor);
};

const formatarPct = (valor, casas = 2) => {
  if (valor === undefined || valor === null) return '--%';
  return `${Number(valor).toFixed(casas)}%`;
};

// Cores e Estilos do Terminal Escuro
const CORES = {
  azul: '#3b82f6',
  azulClaro: '#60a5fa',
  verde: '#10b981',
  amarelo: '#f59e0b',
  vermelho: '#ef4444',
  roxo: '#8b5cf6',
  cinzaLinha: '#1e293b',
  cinzaTexto: '#94a3b8',
};

// Configuração Global do Chart.js
if (window.Chart) {
  Chart.defaults.color = CORES.cinzaTexto;
  Chart.defaults.borderColor = CORES.cinzaLinha;
  Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
}

/**
 * Ponto de entrada da aplicação frontend.
 */
document.addEventListener('DOMContentLoaded', async () => {
  configurarNavegacaoAbas();

  try {
    const resposta = await fetch('data/dashboard_data.json');
    if (!resposta.ok) {
      throw new Error(`Erro HTTP ao carregar dados: ${resposta.status}`);
    }
    const dados = await resposta.json();
    inicializarDashboard(dados);
  } catch (erro) {
    console.error('Falha ao carregar dashboard_data.json:', erro);
    document.querySelector('.content-wrapper').innerHTML = `
      <div class="alert-callout" style="border-left-color: var(--color-danger); margin-top: 2rem;">
        <div class="alert-callout-text">
          <h4>Erro ao Carregar Dados Compilados</h4>
          <p>Certifique-se de executar o pipeline analítico para gerar o arquivo <code>dashboard_data.json</code>.</p>
        </div>
      </div>
    `;
  }
});

/**
 * Configura os ouvintes de clique para navegação por abas.
 */
function configurarNavegacaoAbas() {
  const botoes = document.querySelectorAll('.tab-btn');
  const paineis = document.querySelectorAll('.tab-pane');

  botoes.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');

      botoes.forEach((b) => b.classList.remove('active'));
      paineis.forEach((p) => p.classList.remove('active'));

      btn.classList.add('active');
      const painelAtivo = document.getElementById(targetId);
      if (painelAtivo) {
        painelAtivo.classList.add('active');
      }
    });
  });
}

/**
 * Popula KPIs, inicializa os gráficos Chart.js e aciona o simulador.
 * @param {Object} dados - Objeto JSON completo com as séries compiladas.
 */
function inicializarDashboard(dados) {
  preencherMetadadosEKpis(dados);
  renderizarGraficoHistoricoAPProv(dados);
  renderizarReguaCobertura(dados);
  renderizarEvolucaoEstagios(dados);
  renderizarDecomposicaoAP(dados);
  renderizarDispersaoLinhas(dados);
  renderizarMatrizSafras(dados);
  inicializarSimuladorCapital(dados.simulador_capital_base);
}

/**
 * Preenche os cards superiores com os dados da competência mais recente.
 * @param {Object} dados - Objeto JSON consolidado.
 */
function preencherMetadadosEKpis(dados) {
  const meta = dados.metadata;
  const kpis = dados.kpis_topo;

  // Header
  const dtFechamento = new Date(meta.competencia_mais_recente + 'T00:00:00');
  const mesAno = dtFechamento.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
  const elMeta = document.getElementById('meta-competencia');
  if (elMeta) elMeta.textContent = mesAno.toUpperCase();

  // 1. Ativo Problemático
  document.getElementById('kpi-ap-valor').textContent = formatarPct(kpis.taxa_ativo_problematico_pct);
  document.getElementById('kpi-ap-sub').textContent = `Saldo: ${formatarMoeda(kpis.saldo_ativo_problematico)}`;

  // 2. Provisão Constituída e Gap
  document.getElementById('kpi-prov-valor').textContent = formatarPct(kpis.taxa_provisao_pct);
  document.getElementById('kpi-prov-sub').textContent = `Estoque: ${formatarMoeda(kpis.saldo_provisao_constituida)}`;
  const elGapTag = document.getElementById('kpi-prov-tag');
  const gap = Number(kpis.gap_cobertura_pct);
  elGapTag.textContent = `Gap: ${gap > 0 ? '+' : ''}${formatarPct(gap)}`;
  elGapTag.className = gap < 0 ? 'kpi-badge danger' : 'kpi-badge success';

  // 3. CoR 12M
  const ultSerie = dados.serie_temporal_mensal[dados.serie_temporal_mensal.length - 1];
  document.getElementById('kpi-cor-valor').textContent = formatarPct(ultSerie.percentual_cor_12m || 0);

  // 4. Over90 no AP
  document.getElementById('kpi-over90-valor').textContent = formatarPct(kpis.percentual_over90_no_ap_pct);
  document.getElementById('kpi-over90-sub').textContent = `Over90: ${formatarMoeda(kpis.saldo_over90)}`;

  // Alerta de Cruzamento
  const cruzamento = dados.serie_temporal_mensal.find((s) => s.cruzamento_alerta);
  if (cruzamento) {
    const dtCruz = new Date(cruzamento.data_fechamento + 'T00:00:00');
    const mesCruz = dtCruz.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
    document.getElementById('alerta-cruzamento-titulo').textContent =
      `Ponto Crítico Identificado: Em ${mesCruz}, a Provisão cruzou abaixo do Ativo Problemático`;
    document.getElementById('alerta-cruzamento-desc').textContent =
      `Nesta data, Taxa de Provisão (${formatarPct(cruzamento.taxa_provisao)}) ficou inferior à Taxa de AP (${formatarPct(cruzamento.taxa_ap)}), gerando um Gap de Cobertura de ${formatarPct(cruzamento.gap_cobertura)}.`;
  }
}

/**
 * Gráfico 1: Evolução Histórica da Taxa de AP vs. Provisão vs. SNCC Bacen.
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarGraficoHistoricoAPProv(dados) {
  const ctx = document.getElementById('chart-historico-ap-prov');
  if (!ctx) return;

  const labels = dados.serie_temporal_mensal.map((s) => {
    const d = new Date(s.data_fechamento + 'T00:00:00');
    return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
  });

  const serieAP = dados.serie_temporal_mensal.map((s) => s.taxa_ap);
  const serieProv = dados.serie_temporal_mensal.map((s) => s.taxa_provisao);

  // Média de AP do SNCC via IF.data
  const ifdataSNCC = dados.benchmarking_ifdata.filter(
    (b) => b.segmento_analise === 'SNCC Consolidado'
  );
  const taxaMediaSNCC = ifdataSNCC.length > 0 ? Number(ifdataSNCC[0].percentual_ap_ifdata) * 100 : 5.3;
  const serieSNCC = labels.map(() => taxaMediaSNCC);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Taxa de Ativo Problemático (Singular)',
          data: serieAP,
          borderColor: CORES.vermelho,
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 2.5,
          tension: 0.25,
          pointRadius: 3,
        },
        {
          label: 'Taxa de Provisão Constituída (Singular)',
          data: serieProv,
          borderColor: CORES.azul,
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2.5,
          tension: 0.25,
          pointRadius: 3,
        },
        {
          label: 'Média de AP do SNCC (IF.data Bacen)',
          data: serieSNCC,
          borderColor: CORES.roxo,
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label}: ${item.parsed.y.toFixed(2)}%`,
          },
        },
      },
      scales: {
        y: {
          ticks: { callback: (val) => `${val}%` },
        },
      },
    },
  });
}

/**
 * Gráfico 2: Régua de Cobertura da Perda Esperada vs REF.
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarReguaCobertura(dados) {
  const ctx = document.getElementById('chart-regua-cobertura');
  if (!ctx) return;

  const cobSingular = Number(dados.kpis_topo.indice_cobertura_ecl || 1.0);
  const refSNCC = dados.benchmarking_ref.find((r) => r.segmento === 'SNCC');
  const refSFN = dados.benchmarking_ref.find((r) => r.segmento === 'SFN');

  const cobSNCC = refSNCC ? Number(refSNCC.indice_cobertura_perda_esperada) : 1.03;
  const cobSFN = refSFN ? Number(refSFN.indice_cobertura_perda_esperada) : 0.98;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Cooperativa Singular', 'SNCC (REF Bacen)', 'SFN Total (REF)'],
      datasets: [
        {
          label: 'Índice de Cobertura (Provisão / ECL)',
          data: [cobSingular, cobSNCC, cobSFN],
          backgroundColor: [
            cobSingular >= 1.0 ? CORES.verde : CORES.vermelho,
            CORES.azul,
            CORES.roxo,
          ],
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => `Cobertura: ${item.parsed.y.toFixed(3)}x`,
          },
        },
      },
      scales: {
        y: {
          min: 0.8,
          ticks: { callback: (val) => `${val.toFixed(2)}x` },
        },
      },
    },
  });
}

/**
 * Gráfico 3: Evolução dos Estágios 1, 2 e 3 (Resolução 4.966).
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarEvolucaoEstagios(dados) {
  const ctx = document.getElementById('chart-evolucao-estagios');
  if (!ctx) return;

  const labels = dados.evolucao_estagios_mensal.map((e) => {
    const d = new Date(e.data_fechamento + 'T00:00:00');
    return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
  });

  const est1 = dados.evolucao_estagios_mensal.map((e) => e.estagio_1_saldo);
  const est2 = dados.evolucao_estagios_mensal.map((e) => e.estagio_2_saldo);
  const est3 = dados.evolucao_estagios_mensal.map((e) => e.estagio_3_saldo);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Estágio 1 (Risco Inicial)',
          data: est1,
          backgroundColor: CORES.verde,
          stack: 'estagios',
        },
        {
          label: 'Estágio 2 (SICR - Alerta)',
          data: est2,
          backgroundColor: CORES.amarelo,
          stack: 'estagios',
        },
        {
          label: 'Estágio 3 (Ativo Problemático)',
          data: est3,
          backgroundColor: CORES.vermelho,
          stack: 'estagios',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label}: ${formatarMoeda(item.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { stacked: true },
        y: {
          stacked: true,
          ticks: { callback: (val) => formatarMoeda(val) },
        },
      },
    },
  });
}

/**
 * Gráfico 4: Quebra da Origem do Ativo Problemático (Rosca).
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarDecomposicaoAP(dados) {
  const ctx = document.getElementById('chart-decomposicao-ap');
  if (!ctx) return;

  const dec = dados.decomposicao_ap;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: [
        'Atraso Prolongado (>90d)',
        'Renegociação por Estresse (Forbearance)',
        'Deterioração Rating / Preventivos',
      ],
      datasets: [
        {
          data: [dec.saldo_over90, dec.saldo_renegociacao, dec.saldo_outros_preventivos],
          backgroundColor: [CORES.vermelho, CORES.amarelo, CORES.roxo],
          borderWidth: 2,
          borderColor: '#0f172a',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right' },
        tooltip: {
          callbacks: {
            label: (item) => `${item.label}: ${formatarMoeda(item.raw)}`,
          },
        },
      },
    },
  });
}

/**
 * Gráfico 5: Dispersão por Linha de Crédito (Saldo vs Taxa de Provisão).
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarDispersaoLinhas(dados) {
  const ctx = document.getElementById('chart-dispersao-linhas');
  if (!ctx) return;

  const linhas = dados.dispersao_linhas;
  const labels = linhas.map((l) => l.nome_linha);
  const volumes = linhas.map((l) => l.saldo_linha);
  const taxas = linhas.map((l) => l.taxa_risco_linha);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Saldo da Carteira (R$)',
          data: volumes,
          backgroundColor: 'rgba(59, 130, 246, 0.4)',
          borderColor: CORES.azul,
          borderWidth: 1,
          yAxisID: 'yVolume',
        },
        {
          label: 'Taxa de Provisão (%)',
          data: taxas,
          type: 'line',
          borderColor: CORES.vermelho,
          borderWidth: 2,
          pointRadius: 4,
          yAxisID: 'yTaxa',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        yVolume: {
          type: 'linear',
          position: 'left',
          ticks: { callback: (val) => formatarMoeda(val) },
        },
        yTaxa: {
          type: 'linear',
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { callback: (val) => `${val}%` },
        },
      },
    },
  });
}

/**
 * Gráfico 6: Matriz de Safras (Vintage por MOB).
 * @param {Object} dados - Objeto JSON consolidado.
 */
function renderizarMatrizSafras(dados) {
  const ctx = document.getElementById('chart-vintages');
  if (!ctx) return;

  const vintages = dados.matriz_safras_vintages;
  const safras = [...new Set(vintages.map((v) => v.safra))].sort();
  const mobs = [1, 3, 6, 12, 24];

  const coresPaleta = [CORES.azul, CORES.verde, CORES.amarelo, CORES.vermelho, CORES.roxo];

  const datasets = safras.slice(-5).map((safra, idx) => {
    const dadosSafra = vintages.filter((v) => v.safra === safra);
    const dataPoints = mobs.map((m) => {
      const ponto = dadosSafra.find((d) => d.mob === m);
      return ponto ? Number(ponto.taxa_ativo_problematico) * 100 : null;
    });

    const cor = coresPaleta[idx % coresPaleta.length];
    return {
      label: `Safra ${safra}`,
      data: dataPoints,
      borderColor: cor,
      backgroundColor: cor,
      tension: 0.2,
      spanGaps: true,
    };
  });

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: mobs.map((m) => `MOB ${m}`),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (item) => `${item.dataset.label}: ${item.parsed.y ? item.parsed.y.toFixed(2) + '%' : 'N/A'}`,
          },
        },
      },
      scales: {
        y: {
          ticks: { callback: (val) => `${val}%` },
        },
      },
    },
  });
}

/**
 * Inicializa e gerencia a reatividade do Simulador de Capital What-If.
 * @param {Object} base - Parâmetros base contábeis e de capital.
 */
function inicializarSimuladorCapital(base) {
  const slider = document.getElementById('stress-slider');
  const valorDisplay = document.getElementById('slider-valor-display');

  const elDeltaProv = document.getElementById('sim-delta-provisao');
  const elSobrasAtual = document.getElementById('sim-sobras-atual');
  const elSobrasProjetada = document.getElementById('sim-sobras-projetada');
  const elSobrasPct = document.getElementById('sim-sobras-impacto-pct');
  const elCapAtual = document.getElementById('sim-capital-atual');
  const elCapProjetado = document.getElementById('sim-capital-projetado');

  const recarcular = () => {
    const deltaAPPct = parseFloat(slider.value);
    valorDisplay.textContent = `+${deltaAPPct.toFixed(1)}%`;

    // 1. Aumento nominal de AP em função da carteira total
    const volumeNovoAP = base.carteira_total * (deltaAPPct / 100);

    // 2. Provisão adicional média requerida (~50% de provisão sobre os novos ativos em default/AP)
    const adicionalProvisao = volumeNovoAP * 0.5;

    // 3. Impacto nas Sobras Líquidas
    const sobrasAtual = base.sobras_atuais;
    const sobrasProjetada = sobrasAtual - adicionalProvisao;
    const variacaoSobrasPct = ((sobrasProjetada - sobrasAtual) / sobrasAtual) * 100;

    // 4. Impacto no Patrimônio de Referência e Índice de Basileia
    const prAtual = base.patrimonio_referencia;
    const rwa = base.rwa_risco_credito;
    const prProjetado = prAtual - adicionalProvisao;
    const basileiaAtual = (prAtual / rwa) * 100;
    const basileiaProjetada = (prProjetado / rwa) * 100;

    // Atualização do DOM
    elDeltaProv.textContent = `+ ${formatarMoeda(adicionalProvisao)}`;

    elSobrasAtual.textContent = formatarMoeda(sobrasAtual);
    elSobrasProjetada.textContent = formatarMoeda(sobrasProjetada);
    elSobrasProjetada.className = `impact-simulated ${sobrasProjetada >= 0 ? 'positive' : 'negative'}`;
    elSobrasPct.textContent = `Variação nas Sobras: ${variacaoSobrasPct.toFixed(1)}%`;

    elCapAtual.textContent = formatarPct(basileiaAtual);
    elCapProjetado.textContent = formatarPct(basileiaProjetada);
    elCapProjetado.className = `impact-simulated ${basileiaProjetada >= 11.0 ? 'positive' : 'negative'}`;
  };

  slider.addEventListener('input', recarcular);
  recarcular(); // Execução inicial
}
