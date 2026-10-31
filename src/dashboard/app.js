/**
 * @fileoverview Aplicação cliente nativa Vanilla JS para o painel executivo Radar 4966.
 * Consome os dados compilados em data/dashboard_data.json e inicializa as visualizações
 * interativas via Chart.js, além do simulador reativo de capital e sensibilidade.
 */

// ============================================================================
// Utilitários de Formatação
// ============================================================================

/**
 * Formata um valor numérico no padrão monetário brasileiro (BRL).
 * @param {number} valor - Valor numérico a formatar.
 * @returns {string} String formatada em reais sem centavos.
 */
const formatarMoeda = (valor) => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(valor);
};

/**
 * Formata um valor numérico em percentual.
 * @param {number|null|undefined} valor - Valor percentual a formatar.
 * @param {number} [casas=2] - Quantidade de casas decimais.
 * @returns {string} String percentual formatada.
 */
const formatarPct = (valor, casas = 2) => {
  if (valor === undefined || valor === null || isNaN(valor)) return '--%';
  return `${Number(valor).toFixed(casas)}%`;
};

// ============================================================================
// Paleta de Cores e Configurações Visuais do Terminal Escuro
// ============================================================================
const CORES = {
  azul: '#3b82f6',
  azulClaro: '#60a5fa',
  azulGrad: 'rgba(59, 130, 246, 0.15)',
  verde: '#10b981',
  verdeGrad: 'rgba(16, 185, 129, 0.2)',
  amarelo: '#f59e0b',
  amareloGrad: 'rgba(245, 158, 11, 0.2)',
  vermelho: '#ef4444',
  vermelhoGrad: 'rgba(239, 68, 68, 0.15)',
  roxo: '#8b5cf6',
  ciano: '#06b6d4',
  cinzaLinha: '#1e293b',
  cinzaTexto: '#94a3b8',
  cinzaCard: '#0f172a',
  branco: '#ffffff',
};

// Configuração Global de Estilos do Chart.js
if (window.Chart) {
  Chart.defaults.color = CORES.cinzaTexto;
  Chart.defaults.borderColor = CORES.cinzaLinha;
  Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
  Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
  Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
  Chart.defaults.plugins.tooltip.borderColor = '#334155';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 6;
}

// Instâncias globais dos gráficos para recriação e filtragem dinâmica
let chartHistorico = null;
let chartRegua = null;
let chartEvolucaoEstagios = null;
let chartDecomposicao = null;
let chartDispersao = null;
let chartVintages = null;

// Estado global de visualização de estágios: 'nominal' (R$) ou 'pct' (%)
let modoExibicaoEstagios = 'nominal';
let serieEstagiosAtiva = [];

// ============================================================================
// Ponto de Entrada da Aplicação
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  configurarNavegacaoAbas();
  configurarModais();

  try {
    const resposta = await fetch('data/dashboard_data.json');
    if (!resposta.ok) {
      throw new Error(`Erro HTTP ao carregar dados: ${resposta.status}`);
    }
    const dados = await resposta.json();
    inicializarDashboard(dados);
  } catch (erro) {
    console.error('Falha ao carregar dashboard_data.json:', erro);
    const wrapper = document.querySelector('.content-wrapper');
    if (wrapper) {
      wrapper.innerHTML = `
        <div class="alert-callout" style="border-left-color: var(--color-danger); margin-top: 2rem;">
          <div class="alert-callout-icon">❌</div>
          <div class="alert-callout-content">
            <h4>Erro ao Carregar Dados Compilados</h4>
            <p>Não foi possível carregar o arquivo <code>dashboard_data.json</code>. Certifique-se de executar o exportador de dados analíticos.</p>
          </div>
        </div>
      `;
    }
  }
});

// ============================================================================
// Navegação por Abas Executivas
// ============================================================================
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

// ============================================================================
// Modais Executivos: Briefing da Diretoria & Glossário Regulatório
// ============================================================================
function configurarModais() {
  const modalBriefing = document.getElementById('modal-briefing');
  const modalGlossario = document.getElementById('modal-glossario');

  const btnOpenBriefing = document.getElementById('btn-open-briefing');
  const btnCloseBriefing = document.getElementById('btn-close-briefing');
  const btnDismissBriefing = document.getElementById('btn-dismiss-briefing');
  const btnPrintBriefing = document.getElementById('btn-print-briefing');

  const btnOpenGlossario = document.getElementById('btn-open-glossario');
  const btnCloseGlossario = document.getElementById('btn-close-glossario');
  const btnDismissGlossario = document.getElementById('btn-dismiss-glossario');

  const abrirModal = (modal) => {
    if (modal) modal.classList.add('active');
  };

  const fecharModal = (modal) => {
    if (modal) modal.classList.remove('active');
  };

  // Briefing
  if (btnOpenBriefing) btnOpenBriefing.addEventListener('click', () => abrirModal(modalBriefing));
  if (btnCloseBriefing) btnCloseBriefing.addEventListener('click', () => fecharModal(modalBriefing));
  if (btnDismissBriefing) btnDismissBriefing.addEventListener('click', () => fecharModal(modalBriefing));
  if (btnPrintBriefing) {
    btnPrintBriefing.addEventListener('click', () => {
      window.print();
    });
  }

  // Glossário
  if (btnOpenGlossario) btnOpenGlossario.addEventListener('click', () => abrirModal(modalGlossario));
  if (btnCloseGlossario) btnCloseGlossario.addEventListener('click', () => fecharModal(modalGlossario));
  if (btnDismissGlossario) btnDismissGlossario.addEventListener('click', () => fecharModal(modalGlossario));

  // Fechar ao clicar fora da caixa do modal
  [modalBriefing, modalGlossario].forEach((modal) => {
    if (modal) {
      modal.addEventListener('click', (evento) => {
        if (evento.target === modal) {
          fecharModal(modal);
        }
      });
    }
  });

  // Fechar no teclado com tecla 'Escape'
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') {
      fecharModal(modalBriefing);
      fecharModal(modalGlossario);
    }
  });
}

// ============================================================================
// Inicialização Global dos Gráficos e Componentes
// ============================================================================
function inicializarDashboard(dados) {
  serieEstagiosAtiva = dados.evolucao_estagios_mensal;

  preencherMetadadosEKpis(dados);
  renderizarGraficoHistoricoAPProv(dados.serie_temporal_mensal, dados);
  renderizarReguaCobertura(dados);
  renderizarEvolucaoEstagios(serieEstagiosAtiva);
  renderizarDecomposicaoAP(dados);
  renderizarDispersaoLinhas(dados);
  renderizarMatrizSafras(dados);
  inicializarSimuladorCapital(dados.simulador_capital_base);
  configurarFiltroPeriodos(dados);
  configurarAlternadorEstagios();
}

// ============================================================================
// Filtros Temporais (Série Completa, Pré-4.966, Vigência, 12M)
// ============================================================================
function configurarFiltroPeriodos(dados) {
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');

      const periodo = chip.getAttribute('data-period');
      let serieFiltrada = dados.serie_temporal_mensal;
      let estagiosFiltrados = dados.evolucao_estagios_mensal;

      if (periodo === 'pre') {
        // 5 Anos Anteriores à Res. 4.966 (2020 a 2024)
        serieFiltrada = dados.serie_temporal_mensal.filter((s) => s.data_fechamento < '2025-01-01');
        estagiosFiltrados = dados.evolucao_estagios_mensal.filter((e) => e.data_fechamento < '2025-01-01');
      } else if (periodo === 'post') {
        // Vigência Plena da Res. 4.966 (2025 a 2026)
        serieFiltrada = dados.serie_temporal_mensal.filter((s) => s.data_fechamento >= '2025-01-01');
        estagiosFiltrados = dados.evolucao_estagios_mensal.filter((e) => e.data_fechamento >= '2025-01-01');
      } else if (periodo === '12m') {
        // Últimos 12 Meses
        serieFiltrada = dados.serie_temporal_mensal.slice(-12);
        estagiosFiltrados = dados.evolucao_estagios_mensal.slice(-12);
      }

      serieEstagiosAtiva = estagiosFiltrados;
      renderizarGraficoHistoricoAPProv(serieFiltrada, dados);
      renderizarEvolucaoEstagios(serieEstagiosAtiva);
    });
  });
}

// ============================================================================
// Cards de Metadados e KPIs de Topo
// ============================================================================
function preencherMetadadosEKpis(dados) {
  const meta = dados.metadata;
  const kpis = dados.kpis_topo;
  const capBase = dados.simulador_capital_base;

  // Header Metadados
  const dtFechamento = new Date(meta.competencia_mais_recente + 'T00:00:00');
  const mesAno = dtFechamento.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
  const elMeta = document.getElementById('meta-competencia');
  if (elMeta) elMeta.textContent = mesAno.toUpperCase();

  // 1. Ativo Problemático (AP)
  const elApValor = document.getElementById('kpi-ap-valor');
  const elApSub = document.getElementById('kpi-ap-sub');
  if (elApValor) elApValor.textContent = formatarPct(kpis.taxa_ativo_problematico_pct);
  if (elApSub) elApSub.textContent = `Saldo: ${formatarMoeda(kpis.saldo_ativo_problematico)}`;

  // 2. Provisão Constituída e Gap de Cobertura
  const elProvValor = document.getElementById('kpi-prov-valor');
  const elProvSub = document.getElementById('kpi-prov-sub');
  const elGapTag = document.getElementById('kpi-prov-tag');
  if (elProvValor) elProvValor.textContent = formatarPct(kpis.taxa_provisao_pct);
  if (elProvSub) elProvSub.textContent = `Estoque: ${formatarMoeda(kpis.saldo_provisao_constituida)}`;
  if (elGapTag) {
    const gap = Number(kpis.gap_cobertura_pct);
    elGapTag.textContent = `Gap: ${gap > 0 ? '+' : ''}${formatarPct(gap)}`;
    elGapTag.className = gap < 0 ? 'kpi-badge danger' : 'kpi-badge success';
  }

  // 3. Cost of Risk 12M
  const ultSerie = dados.serie_temporal_mensal[dados.serie_temporal_mensal.length - 1];
  const elCorValor = document.getElementById('kpi-cor-valor');
  if (elCorValor) elCorValor.textContent = formatarPct(ultSerie.percentual_cor_12m || 0);

  // 4. Over90 no Ativo Problemático
  const elOver90Valor = document.getElementById('kpi-over90-valor');
  const elOver90Sub = document.getElementById('kpi-over90-sub');
  if (elOver90Valor) elOver90Valor.textContent = formatarPct(kpis.percentual_over90_no_ap_pct);
  if (elOver90Sub) elOver90Sub.textContent = `Over90: ${formatarMoeda(kpis.saldo_over90)}`;

  // 5. Índice de Basileia e Solvência
  const elBasileiaValor = document.getElementById('kpi-basileia-valor');
  const elBasileiaSub = document.getElementById('kpi-basileia-sub');
  if (capBase && elBasileiaValor) {
    elBasileiaValor.textContent = formatarPct(capBase.indice_capital_atual_pct);
    const folga = capBase.indice_capital_atual_pct - 10.5;
    if (elBasileiaSub) {
      elBasileiaSub.textContent = `Folga Prudencial: +${folga.toFixed(2)} p.p.`;
    }
  }

  // Alerta de Inflexão Histórica (Cruzamento)
  const cruzamento = dados.serie_temporal_mensal.find((s) => s.cruzamento_alerta);
  if (cruzamento) {
    const dtCruz = new Date(cruzamento.data_fechamento + 'T00:00:00');
    const mesCruz = dtCruz.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
    const elCruzTitulo = document.getElementById('alerta-cruzamento-titulo');
    const elCruzDesc = document.getElementById('alerta-cruzamento-desc');
    if (elCruzTitulo) {
      elCruzTitulo.textContent = `Ponto Crítico Histórico Identificado: Em ${mesCruz}, a Provisão cruzou abaixo do Ativo Problemático`;
    }
    if (elCruzDesc) {
      elCruzDesc.textContent = `Nesta data de corte, a Taxa de Provisão (${formatarPct(cruzamento.taxa_provisao)}) descolou para baixo da Taxa de Ativo Problemático (${formatarPct(cruzamento.taxa_ap)}), abrindo um gap inicial de ${formatarPct(cruzamento.gap_cobertura)}. Sob a Resolução 4.966, a gestão ativa desse gap é indispensável para evitar pressões repentinas de capital.`;
    }
  }
}

// ============================================================================
// Gráfico 1: Evolução Histórica (AP vs. Provisão vs. SNCC)
// ============================================================================
function renderizarGraficoHistoricoAPProv(serieMensal, dados) {
  const ctx = document.getElementById('chart-historico-ap-prov');
  if (!ctx) return;

  if (chartHistorico) {
    chartHistorico.destroy();
  }

  const labels = serieMensal.map((s) => {
    const d = new Date(s.data_fechamento + 'T00:00:00');
    return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
  });

  const serieAP = serieMensal.map((s) => s.taxa_ap);
  const serieProv = serieMensal.map((s) => s.taxa_provisao);

  // Média de AP do SNCC via IF.data
  const ifdataSNCC = dados.benchmarking_ifdata.filter(
    (b) => b.segmento_analise === 'SNCC Consolidado'
  );
  const taxaMediaSNCC = ifdataSNCC.length > 0
    ? Number(ifdataSNCC[ifdataSNCC.length - 1].percentual_ap_ifdata) * 100
    : 5.3;
  const serieSNCC = labels.map(() => taxaMediaSNCC);

  // Marcadores visuais em pontos-chave
  const pointRadii = serieMensal.map((s) => {
    if (s.marco_transicao_4966) return 7;
    if (s.cruzamento_alerta) return 6;
    return 2.5;
  });

  const pointColors = serieMensal.map((s) => {
    if (s.marco_transicao_4966) return CORES.amarelo;
    if (s.cruzamento_alerta) return CORES.vermelho;
    return CORES.azul;
  });

  chartHistorico = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Taxa de Ativo Problemático (Singular)',
          data: serieAP,
          borderColor: CORES.vermelho,
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          fill: true,
          borderWidth: 2.8,
          tension: 0.25,
          pointRadius: pointRadii,
          pointHoverRadius: 8,
          pointBackgroundColor: CORES.vermelho,
        },
        {
          label: 'Taxa de Provisão Constituída (Singular)',
          data: serieProv,
          borderColor: CORES.azul,
          backgroundColor: 'rgba(59, 130, 246, 0.08)',
          fill: true,
          borderWidth: 2.8,
          tension: 0.25,
          pointRadius: pointRadii,
          pointHoverRadius: 8,
          pointBackgroundColor: pointColors,
        },
        {
          label: 'Média de AP do SNCC (IF.data Bacen)',
          data: serieSNCC,
          borderColor: CORES.roxo,
          borderDash: [5, 4],
          borderWidth: 2,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 14,
            usePointStyle: true,
            padding: 15,
            color: '#cbd5e1',
          },
        },
        tooltip: {
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              const item = serieMensal[idx];
              const dt = new Date(item.data_fechamento + 'T00:00:00');
              const nomeMes = dt.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
              const regime = item.regime_normativo || (item.vigencia_4966 ? 'Res. 4.966' : 'Pré-4.966');
              return `${nomeMes.toUpperCase()} • ${regime}`;
            },
            label: (item) => {
              return `  ${item.dataset.label}: ${item.parsed.y.toFixed(2)}%`;
            },
            afterBody: (items) => {
              const idx = items[0].dataIndex;
              const item = serieMensal[idx];
              const linhas = [];
              const gap = (item.taxa_provisao - item.taxa_ap).toFixed(2);
              linhas.push(`  Gap de Cobertura: ${gap}%`);
              if (item.percentual_cor_12m) {
                linhas.push(`  Cost of Risk 12M: ${item.percentual_cor_12m.toFixed(2)}%`);
              }
              if (item.marco_transicao_4966) {
                linhas.push('  ⭐ MARCO HISTÓRICO: Entrada em vigor da Resolução CMN 4.966');
              }
              if (item.cruzamento_alerta) {
                linhas.push('  ⚠️ ALERTA: Inflexão de cobertura de risco');
              }
              return linhas;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
        },
        y: {
          ticks: { callback: (val) => `${val}%` },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
      },
    },
  });
}

// ============================================================================
// Gráfico 2: Régua de Cobertura da Perda Esperada vs. REF
// ============================================================================
function renderizarReguaCobertura(dados) {
  const ctx = document.getElementById('chart-regua-cobertura');
  if (!ctx) return;

  if (chartRegua) {
    chartRegua.destroy();
  }

  const cobSingular = Number(dados.kpis_topo.indice_cobertura_ecl || 1.0);
  const refSNCC = dados.benchmarking_ref.find((r) => r.segmento === 'SNCC');
  const refSFN = dados.benchmarking_ref.find((r) => r.segmento === 'SFN');

  const cobSNCC = refSNCC ? Number(refSNCC.indice_cobertura_perda_esperada) : 1.03;
  const cobSFN = refSFN ? Number(refSFN.indice_cobertura_perda_esperada) : 0.98;

  chartRegua = new Chart(ctx, {
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
          borderWidth: 1,
          borderColor: [
            cobSingular >= 1.0 ? '#34d399' : '#f87171',
            '#60a5fa',
            '#a78bfa',
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
            title: (items) => items[0].label,
            label: (item) => `  Cobertura ECL: ${item.parsed.y.toFixed(3)}x`,
            afterBody: (items) => {
              const val = items[0].parsed.y;
              if (val >= 1.0) {
                return ['  Status: Conforme com a Resolução CMN 4.966 (≥ 1,00x)'];
              }
              return ['  Status: Déficit de cobertura frente à Perda Esperada (< 1,00x)'];
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
        },
        y: {
          min: 0.85,
          max: 1.15,
          ticks: { callback: (val) => `${val.toFixed(2)}x` },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
      },
    },
  });
}

// ============================================================================
// Gráfico 3: Migração de Estágios 1, 2 e 3 (Nominal R$ vs. Share %)
// ============================================================================
function configurarAlternadorEstagios() {
  const btnNominal = document.getElementById('btn-toggle-estagios-nominal');
  const btnPct = document.getElementById('btn-toggle-estagios-pct');

  if (btnNominal && btnPct) {
    btnNominal.addEventListener('click', () => {
      if (modoExibicaoEstagios === 'nominal') return;
      modoExibicaoEstagios = 'nominal';
      btnNominal.classList.add('active');
      btnPct.classList.remove('active');
      renderizarEvolucaoEstagios(serieEstagiosAtiva);
    });

    btnPct.addEventListener('click', () => {
      if (modoExibicaoEstagios === 'pct') return;
      modoExibicaoEstagios = 'pct';
      btnPct.classList.add('active');
      btnNominal.classList.remove('active');
      renderizarEvolucaoEstagios(serieEstagiosAtiva);
    });
  }
}

function renderizarEvolucaoEstagios(estagiosMensal) {
  const ctx = document.getElementById('chart-evolucao-estagios');
  if (!ctx) return;

  if (chartEvolucaoEstagios) {
    chartEvolucaoEstagios.destroy();
  }

  const labels = estagiosMensal.map((e) => {
    const d = new Date(e.data_fechamento + 'T00:00:00');
    return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
  });

  const isPct = modoExibicaoEstagios === 'pct';

  const est1 = estagiosMensal.map((e) => isPct ? Number(e.estagio_1_pct) : Number(e.estagio_1_saldo));
  const est2 = estagiosMensal.map((e) => isPct ? Number(e.estagio_2_pct) : Number(e.estagio_2_saldo));
  const est3 = estagiosMensal.map((e) => isPct ? Number(e.estagio_3_pct) : Number(e.estagio_3_saldo));

  chartEvolucaoEstagios = new Chart(ctx, {
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
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            padding: 12,
            color: '#cbd5e1',
          },
        },
        tooltip: {
          callbacks: {
            label: (item) => {
              if (isPct) {
                return `  ${item.dataset.label}: ${item.parsed.y.toFixed(2)}% da carteira`;
              }
              return `  ${item.dataset.label}: ${formatarMoeda(item.parsed.y)}`;
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
        },
        y: {
          stacked: true,
          max: isPct ? 100 : undefined,
          ticks: {
            callback: (val) => isPct ? `${val}%` : formatarMoeda(val),
          },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
      },
    },
  });
}

// ============================================================================
// Gráfico 4: Quebra da Origem do Ativo Problemático (Rosca)
// ============================================================================
function renderizarDecomposicaoAP(dados) {
  const ctx = document.getElementById('chart-decomposicao-ap');
  if (!ctx) return;

  if (chartDecomposicao) {
    chartDecomposicao.destroy();
  }

  const dec = dados.decomposicao_ap;
  const totalAP = Number(dec.saldo_over90) + Number(dec.saldo_renegociacao) + Number(dec.saldo_outros_preventivos);

  chartDecomposicao = new Chart(ctx, {
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
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            padding: 15,
            color: '#cbd5e1',
          },
        },
        tooltip: {
          callbacks: {
            label: (item) => {
              const valor = item.raw;
              const pct = ((valor / totalAP) * 100).toFixed(1);
              return `  ${item.label}: ${formatarMoeda(valor)} (${pct}%)`;
            },
          },
        },
      },
      cutout: '65%',
    },
  });
}

// ============================================================================
// Gráfico 5: Concentração & Risco por Linha de Crédito
// ============================================================================
function renderizarDispersaoLinhas(dados) {
  const ctx = document.getElementById('chart-dispersao-linhas');
  if (!ctx) return;

  if (chartDispersao) {
    chartDispersao.destroy();
  }

  const linhas = dados.dispersao_linhas;
  const labels = linhas.map((l) => l.nome_linha);
  const volumes = linhas.map((l) => l.saldo_linha);
  const taxas = linhas.map((l) => l.taxa_risco_linha);

  chartDispersao = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Saldo Concedido (R$)',
          data: volumes,
          backgroundColor: 'rgba(59, 130, 246, 0.45)',
          borderColor: CORES.azul,
          borderWidth: 1.5,
          borderRadius: 4,
          yAxisID: 'yVolume',
        },
        {
          label: 'Taxa de Provisão (%)',
          data: taxas,
          type: 'line',
          borderColor: CORES.vermelho,
          backgroundColor: CORES.vermelho,
          borderWidth: 2.5,
          pointRadius: 5,
          pointHoverRadius: 7,
          yAxisID: 'yTaxa',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            color: '#cbd5e1',
          },
        },
        tooltip: {
          callbacks: {
            label: (item) => {
              if (item.dataset.yAxisID === 'yVolume') {
                return `  Saldo Concedido: ${formatarMoeda(item.parsed.y)}`;
              }
              return `  Taxa de Provisão Requerida: ${item.parsed.y.toFixed(2)}%`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
        },
        yVolume: {
          type: 'linear',
          position: 'left',
          ticks: { callback: (val) => formatarMoeda(val) },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
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

// ============================================================================
// Gráfico 6: Matriz de Safras (Vintage por MOB)
// ============================================================================
function renderizarMatrizSafras(dados) {
  const ctx = document.getElementById('chart-vintages');
  if (!ctx) return;

  if (chartVintages) {
    chartVintages.destroy();
  }

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
      borderWidth: 2.2,
      tension: 0.2,
      spanGaps: true,
      pointRadius: 4,
      pointHoverRadius: 7,
    };
  });

  chartVintages = new Chart(ctx, {
    type: 'line',
    data: {
      labels: mobs.map((m) => `MOB ${m} (${m} meses)`),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            padding: 15,
            color: '#cbd5e1',
          },
        },
        tooltip: {
          callbacks: {
            title: (items) => `Maturidade: ${items[0].label}`,
            label: (item) => {
              const val = item.parsed.y;
              return `  ${item.dataset.label}: ${val !== null ? val.toFixed(2) + '%' : 'Sem dados suficientes'}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
        },
        y: {
          ticks: { callback: (val) => `${val}%` },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
        },
      },
    },
  });
}

// ============================================================================
// Simulador What-If de Capital & Sensibilidade
// ============================================================================
function inicializarSimuladorCapital(base) {
  const slider = document.getElementById('stress-slider');
  const valorDisplay = document.getElementById('slider-valor-display');
  const botoesCenario = document.querySelectorAll('.scenario-btn');

  const elDeltaProv = document.getElementById('sim-delta-provisao');
  const elSobrasAtual = document.getElementById('sim-sobras-atual');
  const elSobrasProjetada = document.getElementById('sim-sobras-projetada');
  const elSobrasPct = document.getElementById('sim-sobras-impacto-pct');
  const elCapAtual = document.getElementById('sim-capital-atual');
  const elCapProjetado = document.getElementById('sim-capital-projetado');
  const elMargemBasileia = document.getElementById('sim-margem-basileia');

  const elParecerTexto = document.getElementById('sim-parecer-texto');
  const elStatusTag = document.getElementById('sim-status-tag');

  const recalcular = () => {
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

    // 4. Impacto no Patrimônio de Referência e Índice de Basileia (Piso Bacen: 10,50%)
    const prAtual = base.patrimonio_referencia;
    const rwa = base.rwa_risco_credito;
    const prProjetado = prAtual - adicionalProvisao;
    const basileiaAtual = (prAtual / rwa) * 100;
    const basileiaProjetada = (prProjetado / rwa) * 100;
    const margemSolvencia = basileiaProjetada - 10.5;

    // Atualização dos elementos no DOM
    elDeltaProv.textContent = `+ ${formatarMoeda(adicionalProvisao)}`;

    elSobrasAtual.textContent = formatarMoeda(sobrasAtual);
    elSobrasProjetada.textContent = formatarMoeda(sobrasProjetada);
    elSobrasProjetada.className = `impact-simulated ${sobrasProjetada >= 0 ? 'positive' : 'negative'}`;
    elSobrasPct.textContent = `Variação nas Sobras: ${variacaoSobrasPct.toFixed(1)}%`;

    elCapAtual.textContent = formatarPct(basileiaAtual);
    elCapProjetado.textContent = formatarPct(basileiaProjetada);
    elCapProjetado.className = `impact-simulated ${basileiaProjetada >= 11.5 ? 'positive' : basileiaProjetada >= 10.5 ? 'negative' : 'negative'}`;

    if (elMargemBasileia) {
      elMargemBasileia.textContent = `${margemSolvencia >= 0 ? '+' : ''}${margemSolvencia.toFixed(2)} p.p.`;
      elMargemBasileia.className = `impact-simulated ${margemSolvencia >= 2.0 ? 'positive' : margemSolvencia >= 0 ? 'negative' : 'negative'}`;
    }

    // Parecer Dinâmico da Diretoria de Riscos
    atualizarParecerSensibilidade(deltaAPPct, adicionalProvisao, sobrasProjetada, basileiaProjetada, margemSolvencia, elParecerTexto, elStatusTag);
  };

  // Botões de cenários predefinidos
  botoesCenario.forEach((btn) => {
    btn.addEventListener('click', () => {
      botoesCenario.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      slider.value = btn.getAttribute('data-stress');
      recalcular();
    });
  });

  slider.addEventListener('input', () => {
    // Sincronizar botões de cenário com valor do slider
    botoesCenario.forEach((b) => {
      if (parseFloat(b.getAttribute('data-stress')) === parseFloat(slider.value)) {
        b.classList.add('active');
      } else {
        b.classList.remove('active');
      }
    });
    recalcular();
  });

  recalcular(); // Execução inicial imediata
}

/**
 * Atualiza o parecer executivo dinâmico emitido pela Diretoria de Riscos.
 */
function atualizarParecerSensibilidade(deltaAP, addProv, sobrasProj, basileiaProj, margem, elTexto, elTag) {
  if (!elTexto || !elTag) return;

  if (deltaAP <= 0.8) {
    elTag.textContent = 'Status: Cenário Benigno';
    elTag.className = 'opinion-status-tag';
    elTexto.innerHTML = `Sob um choque controlado de <strong>+${deltaAP.toFixed(1)}%</strong> no AP (consumo de PDD de <strong>${formatarMoeda(addProv)}</strong>), as Sobras Líquidas permanecem em <strong>${formatarMoeda(sobrasProj)}</strong> e o Índice de Basileia fica confortável em <strong>${formatarPct(basileiaProj)}</strong> (folga de <strong>+${margem.toFixed(2)} p.p.</strong> sobre o piso Bacen de 10,50%). Capacidade plena de retenção patrimonial sem necessidade de chamadas de capital.`;
  } else if (deltaAP <= 1.8) {
    elTag.textContent = 'Status: Estresse Moderado';
    elTag.className = 'opinion-status-tag alert';
    elTexto.innerHTML = `Sob estresse moderado de <strong>+${deltaAP.toFixed(1)}%</strong> no AP, a exigência adicional de <strong>${formatarMoeda(addProv)}</strong> em PDD consome parcela expressiva do resultado do exercício (${sobrasProj < 0 ? '<span style="color: var(--color-danger)">Resultado deficitário projetado</span>' : `sobras de <strong>${formatarMoeda(sobrasProj)}</strong>`}). O Índice de Basileia recua para <strong>${formatarPct(basileiaProj)}</strong>, mantendo margem prudencial de <strong>+${margem.toFixed(2)} p.p.</strong> Recomendado contingenciar distribuição de sobras e intensificar renegociações preventivas.`;
  } else {
    elTag.textContent = 'Status: Estresse Severo / Crítico';
    elTag.className = 'opinion-status-tag critical';
    elTexto.innerHTML = `No cenário de estresse severo de <strong>+${deltaAP.toFixed(1)}%</strong> no AP, a necessidade imediata de aporte de <strong>${formatarMoeda(addProv)}</strong> em PDD consome a totalidade das sobras e afeta o Patrimônio Líquido. Embora o Índice de Basileia projetado de <strong>${formatarPct(basileiaProj)}</strong> ainda cumpra formalmente o piso regulatório (margem de <strong>+${margem.toFixed(2)} p.p.</strong>), aciona-se o gatilho de preservação de capital com bloqueio de expansão de ativos ponderados pelo risco.`;
  }
}
