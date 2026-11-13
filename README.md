# Monitor de Carteira e Conferência — Crédito PJ (Cenário ES)

Projeto prático desenvolvido para demonstrar a aplicação de **Python**, **HTML**, **CSS** e **planilhas analíticas** em uma rotina de análise de carteiras de crédito Pessoa Jurídica no Espírito Santo.

> **Aviso:** Todos os contratos, CNPJs, códigos de agência e valores presentes neste repositório são **100% sintéticos e simulados** exclusivamente para fins acadêmicos e de portfólio.

## O que o projeto faz

1. **Higienização e Auditoria em Python (`src/analise_carteira_pj.py`):**
   - Lê a base bruta simulada (`data/contratos_pj_es_bruto.csv`) distribuída entre municípios do ES e linhas de crédito PJ (*Capital de Giro*, *Crédito Investimento*, *Antecipação de Recebíveis* e *Repasse BNDES / FINAME*).
   - Valida integridade cadastral (formatação de CNPJ, código de agência, valores positivos) e sinaliza automaticamente inconsistências e parcelas com atraso acima de 30 dias.
   - Gera o relatório consolidado `data/relatorio_consolidado_pj.csv` (pronto para importação no Google Planilhas ou Excel) e o resumo estruturado `data/resumo_carteira.json`.

2. **Painel Executivo em HTML, CSS e JavaScript (`index.html`, `style.css`, `app.js`):**
   - Exibe KPIs da carteira (Volume Total, Ticket Médio, Inadimplência > 30d e Alertas de Conferência).
   - Permite filtrar dinamicamente por **produto** e **município do ES**.
   - Inclui a fila de conferência para apoio às agências e um guia rápido de enquadramento por linha de crédito.

## Como executar localmente

```bash
# Gerar a base simulada, validar e atualizar os relatórios
uv run python src/analise_carteira_pj.py

# Abrir um servidor local simples para visualizar o painel
python3 -m http.server 8000
```
