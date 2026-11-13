const GUIA_PRODUTOS = {
  "Capital de Giro": {
    publico: "Empresas que precisam reforçar o fluxo de caixa, estoque ou despesas operacionais.",
    prazo: "12 a 36 meses",
    checklist: [
      "Faturamento atualizado e validado na base cadastral",
      "Conferência de certidões e ausência de restrições impeditivas",
      "Definição de garantia (aval dos sócios ou recebíveis)"
    ]
  },
  "Crédito Investimento": {
    publico: "Aquisição de máquinas, equipamentos, reformas e modernização de empresas capixabas.",
    prazo: "36 a 72 meses (com carência negociável)",
    checklist: [
      "Orçamento ou nota pró-forma dos bens financiados",
      "Análise de capacidade de pagamento e projeção de retorno",
      "Registro da alienação fiduciária ou garantia real"
    ]
  },
  "Antecipação de Recebíveis": {
    publico: "Antecipação de vendas em cartão, duplicatas e cheques para liquidez imediata.",
    prazo: "Curto prazo (3 a 12 meses)",
    checklist: [
      "Conferência da agenda de recebíveis e lastro das notas fiscais",
      "Validação de limite operacional aprovado para o CNPJ",
      "Checagem de concentração por sacado"
    ]
  },
  "Repasse BNDES / FINAME": {
    publico: "Expansão industrial, transporte e projetos de energia renovável de longo prazo.",
    prazo: "48 a 84 meses",
    checklist: [
      "Enquadramento do porte da empresa e código FINAME do equipamento",
      "Documentação fiscal e ambiental em conformidade",
      "Validação normativa junto à gerência antes do protocolo"
    ]
  }
};

const formatarBRL = (valor) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);

let dadosGlobais = null;

async function iniciarDashboard() {
  try {
    const resposta = await fetch("data/resumo_carteira.json");
    dadosGlobais = await resposta.json();

    document.getElementById("data-geracao").textContent = dadosGlobais.gerado_em;
    preencherFiltros(dadosGlobais);
    atualizarPainel();
    atualizarGuiaProduto("Capital de Giro");
  } catch (erro) {
    console.error("Erro ao carregar resumo_carteira.json:", erro);
  }
}

function preencherFiltros(dados) {
  const selectProduto = document.getElementById("filtro-produto");
  const selectMunicipio = document.getElementById("filtro-municipio");

  const produtos = [...new Set(dados.contratos_amostra.map((c) => c.produto))].sort();
  const municipios = [...new Set(dados.contratos_amostra.map((c) => c.municipio))].sort();

  produtos.forEach((prod) => {
    const opt = document.createElement("option");
    opt.value = prod;
    opt.textContent = prod;
    selectProduto.appendChild(opt);
  });

  municipios.forEach((mun) => {
    const opt = document.createElement("option");
    opt.value = mun;
    opt.textContent = mun;
    selectMunicipio.appendChild(opt);
  });

  selectProduto.addEventListener("change", atualizarPainel);
  selectMunicipio.addEventListener("change", atualizarPainel);

  document.getElementById("btn-limpar-filtros").addEventListener("click", () => {
    selectProduto.value = "TODOS";
    selectMunicipio.value = "TODOS";
    atualizarPainel();
  });

  document.getElementById("guia-produto").addEventListener("change", (e) => {
    atualizarGuiaProduto(e.target.value);
  });
}

function atualizarPainel() {
  if (!dadosGlobais) return;

  const prodFiltro = document.getElementById("filtro-produto").value;
  const munFiltro = document.getElementById("filtro-municipio").value;

  const contratos = dadosGlobais.contratos_amostra.filter((c) => {
    const okProd = prodFiltro === "TODOS" || c.produto === prodFiltro;
    const okMun = munFiltro === "TODOS" || c.municipio === munFiltro;
    return okProd && okMun;
  });

  const alertasFiltrados = dadosGlobais.alertas_conferencia.filter((a) => {
    const okProd = prodFiltro === "TODOS" || a.produto === prodFiltro;
    const okMun = munFiltro === "TODOS" || a.municipio === munFiltro;
    return okProd && okMun;
  });

  const qtd = contratos.length;
  const volumeTotal = contratos.reduce((acc, c) => acc + c.valor_liberado, 0);
  const ticketMedio = qtd > 0 ? volumeTotal / qtd : 0;
  const inadimplentes = contratos.filter((c) => c.dias_atraso > 30).length;
  const taxaInad = qtd > 0 ? (inadimplentes / qtd) * 100 : 0;

  document.getElementById("kpi-volume").textContent = formatarBRL(volumeTotal);
  document.getElementById("kpi-contratos").textContent = `${qtd} contratos válidos`;
  document.getElementById("kpi-ticket").textContent = formatarBRL(ticketMedio);
  document.getElementById("kpi-inadimplencia").textContent = `${taxaInad.toFixed(1).replace(".", ",")}%`;
  document.getElementById("kpi-alertas").textContent = String(alertasFiltrados.length);

  renderizarProdutos(contratos, volumeTotal);
  renderizarMunicipios(contratos);
  renderizarAlertas(alertasFiltrados);
}

function renderizarProdutos(contratos, volumeTotal) {
  const container = document.getElementById("lista-produtos");
  container.innerHTML = "";

  const mapa = new Map();
  contratos.forEach((c) => {
    if (!mapa.has(c.produto)) {
      mapa.set(c.produto, { nome: c.produto, volume: 0, qtd: 0, atraso: 0 });
    }
    const item = mapa.get(c.produto);
    item.volume += c.valor_liberado;
    item.qtd += 1;
    if (c.dias_atraso > 30) item.atraso += 1;
  });

  const lista = [...mapa.values()].sort((a, b) => b.volume - a.volume);
  if (lista.length === 0) {
    container.innerHTML = "<p class='panel-desc'>Nenhum contrato encontrado para este filtro.</p>";
    return;
  }

  lista.forEach((item) => {
    const pct = volumeTotal > 0 ? (item.volume / volumeTotal) * 100 : 0;
    const inad = item.qtd > 0 ? (item.atraso / item.qtd) * 100 : 0;

    const div = document.createElement("div");
    div.className = "bar-item";
    div.innerHTML = `
      <div class="bar-top">
        <strong>${item.nome}</strong>
        <span>${formatarBRL(item.volume)} (${pct.toFixed(1)}%)</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width: ${pct.toFixed(1)}%"></div>
      </div>
      <div class="bar-meta">${item.qtd} contratos • Inadimplência &gt;30d: ${inad.toFixed(1)}%</div>
    `;
    container.appendChild(div);
  });
}

function renderizarMunicipios(contratos) {
  const tbody = document.getElementById("tabela-municipios");
  tbody.innerHTML = "";

  const mapa = new Map();
  contratos.forEach((c) => {
    if (!mapa.has(c.municipio)) {
      mapa.set(c.municipio, { nome: c.municipio, volume: 0, qtd: 0, atraso: 0 });
    }
    const item = mapa.get(c.municipio);
    item.volume += c.valor_liberado;
    item.qtd += 1;
    if (c.dias_atraso > 30) item.atraso += 1;
  });

  const lista = [...mapa.values()].sort((a, b) => b.volume - a.volume);
  lista.forEach((item) => {
    const inad = item.qtd > 0 ? (item.atraso / item.qtd) * 100 : 0;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${item.nome}</strong></td>
      <td>${item.qtd}</td>
      <td>${formatarBRL(item.volume)}</td>
      <td><span class="pill ${inad > 15 ? "pill-media" : "pill-ok"}">${inad.toFixed(1)}%</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderizarAlertas(alertas) {
  const tbody = document.getElementById("tabela-alertas");
  tbody.innerHTML = "";

  if (alertas.length === 0) {
    tbody.innerHTML = "<tr><td colspan='5'>Nenhum alerta para o filtro selecionado.</td></tr>";
    return;
  }

  alertas.forEach((alerta) => {
    const tr = document.createElement("tr");
    const classe = alerta.severidade === "Alta" ? "pill-alta" : "pill-media";
    tr.innerHTML = `
      <td><strong>${alerta.id_contrato}</strong></td>
      <td>${alerta.agencia}</td>
      <td>${alerta.municipio}</td>
      <td>${alerta.motivo}</td>
      <td><span class="pill ${classe}">${alerta.severidade}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function atualizarGuiaProduto(produto) {
  const info = GUIA_PRODUTOS[produto];
  const container = document.getElementById("guia-detalhes");
  if (!info) return;

  container.innerHTML = `
    <p><strong>Público-alvo:</strong> ${info.publico}</p>
    <p><strong>Prazo típico:</strong> ${info.prazo}</p>
    <p style="margin-top: 8px;"><strong>Checklist de Conferência para Agências:</strong></p>
    <ul>
      ${info.checklist.map((item) => `<li>${item}</li>`).join("")}
    </ul>
  `;
}

iniciarDashboard();
