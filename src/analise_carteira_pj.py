from __future__ import annotations

import csv
import json
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MUNICIPIOS_ES: tuple[str, ...] = (
    "Vitória",
    "Serra",
    "Vila Velha",
    "Cariacica",
    "Linhares",
    "Cachoeiro de Itapemirim",
    "Colatina",
    "Guarapari",
    "Aracruz",
    "São Mateus",
    "Viana",
    "Nova Venécia",
)

PRODUTOS_PJ: tuple[str, ...] = (
    "Capital de Giro",
    "Crédito Investimento",
    "Antecipação de Recebíveis",
    "Repasse BNDES / FINAME",
)

SEGMENTOS_PJ: tuple[str, ...] = (
    "Comércio Varejista",
    "Indústria e Máquinas",
    "Logística e Transporte",
    "Serviços Corporativos",
    "Agronegócio Capixaba",
    "Construção Civil",
)


@dataclass(frozen=True, slots=True)
class ContratoPJ:
    id_contrato: str
    agencia: str
    municipio: str
    cnpj_mascarado: str
    segmento: str
    produto: str
    valor_liberado: float
    prazo_meses: int
    taxa_mensal_pct: float
    dias_atraso: int
    data_contratacao: str


@dataclass(frozen=True, slots=True)
class AlertaConferencia:
    id_contrato: str
    agencia: str
    municipio: str
    produto: str
    motivo: str
    severidade: str


class ResumoGrupo(TypedDict):
    nome: str
    quantidade: int
    volume_total: float
    ticket_medio: float
    inadimplencia_pct: float


class KPIsGerais(TypedDict):
    total_contratos_validos: int
    volume_total_carteira: float
    ticket_medio: float
    taxa_inadimplencia_pct: float
    total_alertas_conferencia: int


class ResumoCarteira(TypedDict):
    gerado_em: str
    aviso_dados: str
    kpis: KPIsGerais
    por_produto: list[ResumoGrupo]
    por_municipio: list[ResumoGrupo]
    alertas_conferencia: list[dict[str, str]]
    contratos_amostra: list[dict[str, str | float | int]]


def _gerar_cnpj_ficticio(rng: random.Random, invalido: bool = False) -> str:
    raiz = rng.randint(10, 99)
    bloco1 = rng.randint(100, 999)
    bloco2 = rng.randint(100, 999)
    dv = rng.randint(10, 99)
    if invalido:
        return f"{raiz}.{bloco1}.XXX/0001-{dv}"
    return f"{raiz}.{bloco1}.{bloco2}/0001-{dv}"


def gerar_base_simulada(caminho_csv: Path, total_registros: int = 120, seed: int = 2026) -> None:
    rng = random.Random(seed)
    data_base = date(2026, 11, 10)
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)

    faixas_valor: dict[str, tuple[float, float]] = {
        "Capital de Giro": (25_000.0, 280_000.0),
        "Crédito Investimento": (80_000.0, 650_000.0),
        "Antecipação de Recebíveis": (15_000.0, 190_000.0),
        "Repasse BNDES / FINAME": (120_000.0, 950_000.0),
    }

    prazos_produto: dict[str, tuple[int, ...]] = {
        "Capital de Giro": (12, 24, 36),
        "Crédito Investimento": (36, 48, 60, 72),
        "Antecipação de Recebíveis": (3, 6, 12),
        "Repasse BNDES / FINAME": (48, 60, 84),
    }

    pesos_municipios: list[int] = [24, 20, 18, 12, 8, 7, 5, 4, 4, 3, 3, 2]

    with caminho_csv.open("w", encoding="utf-8", newline="") as arquivo:
        campos = [
            "id_contrato",
            "agencia",
            "municipio",
            "cnpj_mascarado",
            "segmento",
            "produto",
            "valor_liberado",
            "prazo_meses",
            "taxa_mensal_pct",
            "dias_atraso",
            "data_contratacao",
        ]
        writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        writer.writeheader()

        for indice in range(1, total_registros + 1):
            produto = rng.choice(PRODUTOS_PJ)
            municipio = rng.choices(MUNICIPIOS_ES, weights=pesos_municipios, k=1)[0]
            min_v, max_v = faixas_valor[produto]
            valor = round(rng.uniform(min_v, max_v), 2)
            prazo = rng.choice(prazos_produto[produto])
            taxa = round(rng.uniform(1.15, 2.35), 2)
            dias_atraso = 0 if rng.random() > 0.14 else rng.randint(5, 75)
            agencia = f"AG-{rng.randint(101, 178):03d}"
            cnpj = _gerar_cnpj_ficticio(rng)
            data_ctr = (data_base - timedelta(days=rng.randint(1, 180))).isoformat()

            # Injeta inconsistencias propositais em ~5% dos registros para validar a auditoria
            if indice == 17:
                cnpj = _gerar_cnpj_ficticio(rng, invalido=True)
            elif indice == 43:
                valor = 0.0
            elif indice == 68:
                agencia = ""
            elif indice == 94:
                valor = -15000.0

            writer.writerow(
                {
                    "id_contrato": f"PJ-2026-{indice:04d}",
                    "agencia": agencia,
                    "municipio": municipio,
                    "cnpj_mascarado": cnpj,
                    "segmento": rng.choice(SEGMENTOS_PJ),
                    "produto": produto,
                    "valor_liberado": f"{valor:.2f}",
                    "prazo_meses": str(prazo),
                    "taxa_mensal_pct": f"{taxa:.2f}",
                    "dias_atraso": str(dias_atraso),
                    "data_contratacao": data_ctr,
                }
            )


def validar_e_processar_base(
    caminho_csv: Path,
) -> tuple[list[ContratoPJ], list[AlertaConferencia]]:
    padrao_cnpj = re.compile(r"^\d{2}\.\d{3}\.\d{3}/0001-\d{2}$")
    contratos_validos: list[ContratoPJ] = []
    alertas: list[AlertaConferencia] = []

    with caminho_csv.open("r", encoding="utf-8", newline="") as arquivo:
        reader = csv.DictReader(arquivo, delimiter=";")
        for linha in reader:
            id_contrato = linha["id_contrato"].strip()
            agencia = linha["agencia"].strip()
            municipio = linha["municipio"].strip()
            cnpj = linha["cnpj_mascarado"].strip()
            segmento = linha["segmento"].strip()
            produto = linha["produto"].strip()
            valor = float(linha["valor_liberado"])
            prazo = int(linha["prazo_meses"])
            taxa = float(linha["taxa_mensal_pct"])
            dias_atraso = int(linha["dias_atraso"])
            data_ctr = linha["data_contratacao"].strip()

            if not agencia:
                alertas.append(
                    AlertaConferencia(
                        id_contrato=id_contrato,
                        agencia="N/D",
                        municipio=municipio,
                        produto=produto,
                        motivo="Código da agência ausente no lançamento",
                        severidade="Alta",
                    )
                )
                continue

            if not padrao_cnpj.match(cnpj):
                alertas.append(
                    AlertaConferencia(
                        id_contrato=id_contrato,
                        agencia=agencia,
                        municipio=municipio,
                        produto=produto,
                        motivo=f"CNPJ com formatação inválida ({cnpj})",
                        severidade="Alta",
                    )
                )
                continue

            if valor <= 0.0:
                alertas.append(
                    AlertaConferencia(
                        id_contrato=id_contrato,
                        agencia=agencia,
                        municipio=municipio,
                        produto=produto,
                        motivo=f"Valor liberado inconsistente (R$ {valor:,.2f})",
                        severidade="Alta",
                    )
                )
                continue

            contrato = ContratoPJ(
                id_contrato=id_contrato,
                agencia=agencia,
                municipio=municipio,
                cnpj_mascarado=cnpj,
                segmento=segmento,
                produto=produto,
                valor_liberado=valor,
                prazo_meses=prazo,
                taxa_mensal_pct=taxa,
                dias_atraso=dias_atraso,
                data_contratacao=data_ctr,
            )
            contratos_validos.append(contrato)

            if dias_atraso > 30:
                alertas.append(
                    AlertaConferencia(
                        id_contrato=id_contrato,
                        agencia=agencia,
                        municipio=municipio,
                        produto=produto,
                        motivo=f"Parcela com {dias_atraso} dias de atraso — contatar agência",
                        severidade="Média",
                    )
                )

    return contratos_validos, alertas


def _agrupar_contratos(
    contratos: list[ContratoPJ],
    chave: str,
) -> list[ResumoGrupo]:
    grupos: dict[str, list[ContratoPJ]] = defaultdict(list)
    for contrato in contratos:
        valor_chave = getattr(contrato, chave)
        grupos[str(valor_chave)].append(contrato)

    resultado: list[ResumoGrupo] = []
    for nome, itens in grupos.items():
        qtd = len(itens)
        volume = round(sum(c.valor_liberado for c in itens), 2)
        ticket = round(volume / qtd, 2) if qtd > 0 else 0.0
        inadimplentes = sum(1 for c in itens if c.dias_atraso > 30)
        inadimplencia_pct = round((inadimplentes / qtd) * 100.0, 2) if qtd > 0 else 0.0
        resultado.append(
            {
                "nome": nome,
                "quantidade": qtd,
                "volume_total": volume,
                "ticket_medio": ticket,
                "inadimplencia_pct": inadimplencia_pct,
            }
        )

    resultado.sort(key=lambda item: item["volume_total"], reverse=True)
    return resultado


def gerar_relatorio_consolidado_csv(
    contratos: list[ContratoPJ],
    caminho_saida: Path,
) -> None:
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "id_contrato",
        "agencia",
        "municipio",
        "cnpj_mascarado",
        "segmento",
        "produto",
        "valor_liberado",
        "prazo_meses",
        "taxa_mensal_pct",
        "dias_atraso",
        "status_carteira",
        "data_contratacao",
    ]
    with caminho_saida.open("w", encoding="utf-8-sig", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        writer.writeheader()
        for contrato in contratos:
            status = "Inadimplente (>30d)" if contrato.dias_atraso > 30 else "Adimplente"
            writer.writerow(
                {
                    "id_contrato": contrato.id_contrato,
                    "agencia": contrato.agencia,
                    "municipio": contrato.municipio,
                    "cnpj_mascarado": contrato.cnpj_mascarado,
                    "segmento": contrato.segmento,
                    "produto": contrato.produto,
                    "valor_liberado": f"{contrato.valor_liberado:.2f}".replace(".", ","),
                    "prazo_meses": str(contrato.prazo_meses),
                    "taxa_mensal_pct": f"{contrato.taxa_mensal_pct:.2f}".replace(".", ","),
                    "dias_atraso": str(contrato.dias_atraso),
                    "status_carteira": status,
                    "data_contratacao": contrato.data_contratacao,
                }
            )


def construir_resumo_json(
    contratos: list[ContratoPJ],
    alertas: list[AlertaConferencia],
    caminho_json: Path,
) -> ResumoCarteira:
    qtd_validos = len(contratos)
    volume_total = round(sum(c.valor_liberado for c in contratos), 2)
    ticket_medio = round(volume_total / qtd_validos, 2) if qtd_validos > 0 else 0.0
    inadimplentes = sum(1 for c in contratos if c.dias_atraso > 30)
    taxa_inadimplencia = round((inadimplentes / qtd_validos) * 100.0, 2) if qtd_validos > 0 else 0.0

    resumo: ResumoCarteira = {
        "gerado_em": "2026-11-13",
        "aviso_dados": "Dados 100% sintéticos e simulados para fins acadêmicos e demonstração.",
        "kpis": {
            "total_contratos_validos": qtd_validos,
            "volume_total_carteira": volume_total,
            "ticket_medio": ticket_medio,
            "taxa_inadimplencia_pct": taxa_inadimplencia,
            "total_alertas_conferencia": len(alertas),
        },
        "por_produto": _agrupar_contratos(contratos, "produto"),
        "por_municipio": _agrupar_contratos(contratos, "municipio"),
        "alertas_conferencia": [asdict(a) for a in alertas],
        "contratos_amostra": [asdict(c) for c in contratos],
    }

    caminho_json.parent.mkdir(parents=True, exist_ok=True)
    caminho_json.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resumo


def main() -> None:
    caminho_bruto = DATA_DIR / "contratos_pj_es_bruto.csv"
    caminho_consolidado = DATA_DIR / "relatorio_consolidado_pj.csv"
    caminho_json = DATA_DIR / "resumo_carteira.json"

    gerar_base_simulada(caminho_bruto)
    contratos_validos, alertas = validar_e_processar_base(caminho_bruto)
    gerar_relatorio_consolidado_csv(contratos_validos, caminho_consolidado)
    resumo = construir_resumo_json(contratos_validos, alertas, caminho_json)

    print("Análise concluída com sucesso!")
    print(f"- Contratos válidos: {resumo['kpis']['total_contratos_validos']}")
    print(f"- Volume total: R$ {resumo['kpis']['volume_total_carteira']:,.2f}")
    print(f"- Alertas de conferência: {resumo['kpis']['total_alertas_conferencia']}")


if __name__ == "__main__":
    main()
