"""
Calculadora de Viga Biapoiada — V2
Cálculo de esforços + dimensionamento de armadura passiva por flexão simples
conforme NBR 6118 (concreto C30, aço CA-50, CAA II).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Parâmetros fixos (hardcode — V2 não pede ao usuário)
# ---------------------------------------------------------------------------
FCK_MPA = 25.0          # concreto C25
FYK_MPA = 500.0         # aço CA-50
COB_CM = 3.0            # cobertura nominal (CAA II)
PHI_EST_CM = 0.5        # estribo presumido Ø5,0 mm
PHI_LONG_CM = 1.25      # bitola longitudinal presumida Ø12,5 mm
GAMMA_F = 1.4           # majoração de carga
GAMMA_C = 1.4           # minoração concreto
GAMMA_S = 1.15          # minoração aço
ALPHA_C = 0.85          # bloco retangular simplificado, fck ≤ 50 MPa (NBR 6118 17.2.2)

# Limites de domínio para CA-50 / fck ≤ 50 MPa
CSI_23 = 0.259          # fronteira domínio 2 / 3
CSI_34 = 0.628          # fronteira domínio 3 / 4
CSI_DUCTIL = 0.45       # limite de ductilidade NBR 6118 14.6.4.3

DISCLAIMER = (
    "Ferramenta educacional. Não substitui memorial de cálculo assinado por "
    "profissional habilitado. ART e NBR 6118 seguem valendo. "
    "Responsabilidade técnica é do engenheiro."
)


# ---------------------------------------------------------------------------
# Núcleo de cálculo
# ---------------------------------------------------------------------------
def calcular_esforcos(L_m: float, q_kN_m: float):
    """Retorna (M_max [kN·m], V_max [kN]) para viga biapoiada com q uniforme."""
    M_max = q_kN_m * L_m**2 / 8.0
    V_max = q_kN_m * L_m / 2.0
    return M_max, V_max


def calcular_diagramas(L_m: float, q_kN_m: float, n: int = 100):
    """Discretiza M(x) e V(x) ao longo do vão."""
    x = np.linspace(0.0, L_m, n)
    M = q_kN_m * x * (L_m - x) / 2.0
    V = q_kN_m * (L_m / 2.0 - x)
    return x, M, V


def dimensionar_armadura(b_cm: float, h_cm: float, M_max_kNm: float) -> dict:
    """
    Dimensionamento à flexão simples — viga retangular, armadura simples.
    Trabalha em kN e cm internamente; entrada de M_max em kN·m.
    """
    # Altura útil
    d_cm = h_cm - COB_CM - PHI_EST_CM - PHI_LONG_CM / 2.0

    # Resistências de cálculo
    fcd_MPa = FCK_MPA / GAMMA_C
    fyd_MPa = FYK_MPA / GAMMA_S
    fcd_kNcm2 = fcd_MPa / 10.0   # 1 MPa = 0,1 kN/cm²
    fyd_kNcm2 = fyd_MPa / 10.0

    # Solicitação
    Md_kNm = M_max_kNm * GAMMA_F
    Md_kNcm = Md_kNm * 100.0     # kN·m → kN·cm

    # Limites de armadura (geométricos, dependem só da seção)
    As_min_cm2 = 0.0015 * b_cm * h_cm   # ρ_min = 0,15% (Tabela 17.3, C30)
    As_max_cm2 = 0.04 * b_cm * h_cm     # ρ_max = 4%

    resultado = {
        "d_cm": d_cm,
        "fcd_MPa": fcd_MPa,
        "fyd_MPa": fyd_MPa,
        "Md_kNm": Md_kNm,
        "As_min_cm2": As_min_cm2,
        "As_max_cm2": As_max_cm2,
    }

    # Kmd com αc = 0,85 (NBR 6118 17.2.2, parábola-retângulo simplificado)
    Kmd = Md_kNcm / (ALPHA_C * b_cm * d_cm**2 * fcd_kNcm2)
    resultado["Kmd"] = Kmd

    # Sem solução real para a equação quadrática → seção esmagaria
    if Kmd >= 0.5:
        resultado.update({
            "x_LN_cm": float("nan"),
            "csi": float("nan"),
            "dominio": "Inviável",
            "dom_status": "erro",
            "As_calc_cm2": float("nan"),
            "As_adotado_cm2": float("nan"),
            "status": "erro",
            "mensagem": (
                f"Seção insuficiente: Kmd = {Kmd:.3f} ≥ 0,5 "
                "(equilíbrio impossível com armadura simples)."
            ),
        })
        return resultado

    # Linha neutra e ξ = x/d
    x_LN_cm = d_cm * (1.0 - np.sqrt(1.0 - 2.0 * Kmd)) / 0.8
    csi = x_LN_cm / d_cm
    resultado["x_LN_cm"] = x_LN_cm
    resultado["csi"] = csi

    # Classificação por domínio
    if csi <= CSI_23:
        dominio = "Domínio 2"
        dom_status = "ok"
    elif csi <= CSI_34:
        dominio = "Domínio 3"
        # Dentro do D3, ductilidade NBR 6118 14.6.4.3 exige x/d ≤ 0,45
        dom_status = "ressalva" if csi > CSI_DUCTIL else "ok"
    else:
        dominio = "Domínio 4"
        dom_status = "alerta"
    resultado["dominio"] = dominio
    resultado["dom_status"] = dom_status

    # Área de aço calculada
    As_calc_cm2 = Md_kNcm / (fyd_kNcm2 * (d_cm - 0.4 * x_LN_cm))
    resultado["As_calc_cm2"] = As_calc_cm2

    # As_max bloqueia
    if As_calc_cm2 > As_max_cm2:
        resultado.update({
            "As_adotado_cm2": float("nan"),
            "status": "erro",
            "mensagem": (
                f"As calculado ({As_calc_cm2:.2f} cm²) excede "
                f"As_max ({As_max_cm2:.2f} cm² = 4% A_c). Seção insuficiente."
            ),
        })
        return resultado

    # As_min governa
    if As_calc_cm2 < As_min_cm2:
        resultado["As_adotado_cm2"] = As_min_cm2
        resultado["status"] = "min"
        resultado["mensagem"] = (
            f"Armadura mínima governou: As_calc = {As_calc_cm2:.2f} cm² "
            f"< As_min = {As_min_cm2:.2f} cm²."
        )
    else:
        resultado["As_adotado_cm2"] = As_calc_cm2
        resultado["status"] = "ok"
        resultado["mensagem"] = "Dimensionamento OK por flexão simples."

    return resultado


# ---------------------------------------------------------------------------
# Memória de cálculo (Markdown)
# ---------------------------------------------------------------------------
def montar_memoria(L, q, b, h, descricao, M_max, V_max, r) -> str:
    nome = descricao.strip() if descricao and descricao.strip() else "(sem identificação)"

    def fmt(v, casas=2):
        return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{casas}f}"

    return f"""# Memória de Cálculo — Viga {nome}

## Dados de entrada
- Vão (L): {L:.2f} m
- Carga distribuída (q): {q:.2f} kN/m
- Seção: b = {b:.1f} cm × h = {h:.1f} cm

## Parâmetros adotados
- Concreto: C30 (fck = 30 MPa)
- Aço: CA-50 (fyk = 500 MPa)
- Cobertura nominal: 30 mm (CAA II)
- Estribo presumido: Ø5,0 mm
- Bitola longitudinal presumida: Ø12,5 mm
- Coeficientes: γf = 1,4 · γc = 1,4 · γs = 1,15
- αc = 0,85 (bloco retangular simplificado, NBR 6118 17.2.2)
- Altura útil (d): {fmt(r['d_cm'])} cm
- fcd = {fmt(r['fcd_MPa'])} MPa · fyd = {fmt(r['fyd_MPa'])} MPa

## Esforços
- Momento máximo: M_max = q×L²/8 = {fmt(M_max)} kN·m
- Cortante máximo: V_max = q×L/2 = {fmt(V_max)} kN

## Dimensionamento da armadura
- Md = M_max × 1,4 = {fmt(r['Md_kNm'])} kN·m
- Kmd = Md / (αc × b × d² × fcd) = {fmt(r['Kmd'], 4)}
- Linha neutra: x = {fmt(r.get('x_LN_cm'))} cm  (ξ = x/d = {fmt(r.get('csi'), 4)})
- Domínio: {r['dominio']}
- As calculado: {fmt(r.get('As_calc_cm2'))} cm²
- As mínima (0,15% A_c): {fmt(r['As_min_cm2'])} cm²
- As máxima (4% A_c): {fmt(r['As_max_cm2'])} cm²
- **As adotado: {fmt(r.get('As_adotado_cm2'))} cm²**

Status: {r['mensagem']}

## Pedido para auditoria
Por favor, audite os cálculos acima conforme NBR 6118. Verifique:
1. Fórmulas de dimensionamento estão corretas?
2. Verificação de domínio está adequada?
3. Limite de armadura mínima foi respeitado?
4. Algum aspecto de segurança que faltou considerar?
"""


# ---------------------------------------------------------------------------
# Interface Streamlit
# ---------------------------------------------------------------------------
def render_resultados(M_max, V_max, r):
    st.subheader("Resumo do dimensionamento")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("M_max", f"{M_max:.2f} kN·m")
    col2.metric("V_max", f"{V_max:.2f} kN")

    As_disp = r.get("As_adotado_cm2")
    if As_disp is None or np.isnan(As_disp):
        col3.metric("As adotado", "—")
    else:
        col3.metric("As adotado", f"{As_disp:.2f} cm²")

    dom_icones = {"ok": "✓", "ressalva": "⚠", "alerta": "⚠", "erro": "✗"}
    icone = dom_icones.get(r.get("dom_status", ""), "")
    col4.metric("Domínio", f"{r['dominio']} {icone}".strip())

    st.divider()

    # Mensagens
    if r["status"] == "ok":
        st.success(r["mensagem"])
    elif r["status"] == "min":
        st.warning(r["mensagem"])
    else:
        st.error(r["mensagem"])

    if r.get("dom_status") == "ressalva":
        st.warning(
            f"x/d = {r['csi']:.3f} > 0,45 — limite de ductilidade da NBR 6118 "
            "(item 14.6.4.3). Considerar armadura dupla ou aumentar a seção."
        )
    elif r.get("dom_status") == "alerta":
        st.error(
            f"x/d = {r['csi']:.3f} > 0,628 — Domínio 4: ruptura frágil do "
            "concreto antes do escoamento do aço. Aumentar a seção."
        )

    # Detalhes auxiliares
    with st.expander("Detalhes do cálculo"):
        st.write(
            {
                "d (cm)": round(r["d_cm"], 3),
                "fcd (MPa)": round(r["fcd_MPa"], 3),
                "fyd (MPa)": round(r["fyd_MPa"], 3),
                "Md (kN·m)": round(r["Md_kNm"], 3),
                "Kmd": round(r["Kmd"], 4),
                "x_LN (cm)": (
                    None if np.isnan(r.get("x_LN_cm", float("nan")))
                    else round(r["x_LN_cm"], 3)
                ),
                "ξ = x/d": (
                    None if np.isnan(r.get("csi", float("nan")))
                    else round(r["csi"], 4)
                ),
                "As_min (cm²)": round(r["As_min_cm2"], 3),
                "As_max (cm²)": round(r["As_max_cm2"], 3),
                "As_calc (cm²)": (
                    None if np.isnan(r.get("As_calc_cm2", float("nan")))
                    else round(r["As_calc_cm2"], 3)
                ),
            }
        )


def render_tabela(L, q, b, h, descricao, M_max, V_max, r):
    st.subheader("Tabela consolidada")
    linha = {
        "descricao": descricao or "",
        "L (m)": L,
        "q (kN/m)": q,
        "b (cm)": b,
        "h (cm)": h,
        "d (cm)": round(r["d_cm"], 3),
        "M_max (kN·m)": round(M_max, 3),
        "V_max (kN)": round(V_max, 3),
        "Md (kN·m)": round(r["Md_kNm"], 3),
        "Kmd": round(r["Kmd"], 4),
        "x_LN (cm)": (
            None if np.isnan(r.get("x_LN_cm", float("nan")))
            else round(r["x_LN_cm"], 3)
        ),
        "ξ": (
            None if np.isnan(r.get("csi", float("nan")))
            else round(r["csi"], 4)
        ),
        "Domínio": r["dominio"],
        "As_calc (cm²)": (
            None if np.isnan(r.get("As_calc_cm2", float("nan")))
            else round(r["As_calc_cm2"], 3)
        ),
        "As_min (cm²)": round(r["As_min_cm2"], 3),
        "As_max (cm²)": round(r["As_max_cm2"], 3),
        "As_adotado (cm²)": (
            None if np.isnan(r.get("As_adotado_cm2", float("nan")))
            else round(r["As_adotado_cm2"], 3)
        ),
        "Status": r["mensagem"],
    }
    df = pd.DataFrame([linha])
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    nome_arq = (descricao.strip() or "viga").replace(" ", "_") + ".csv"
    st.download_button(
        "⬇️ Baixar CSV",
        data=csv,
        file_name=nome_arq,
        mime="text/csv",
    )


def render_diagramas(L, q, descricao):
    x, M, V = calcular_diagramas(L, q, n=100)

    titulo = f"Viga {descricao.strip()}" if descricao and descricao.strip() else "Viga"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Momento fletor M(x) [kN·m]",
                        "Esforço cortante V(x) [kN]"),
        vertical_spacing=0.12,
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=M, mode="lines", name="M(x)",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy", fillcolor="rgba(31,119,180,0.15)",
            hovertemplate="x = %{x:.2f} m<br>M = %{y:.2f} kN·m<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=V, mode="lines", name="V(x)",
            line=dict(color="#d62728", width=2),
            fill="tozeroy", fillcolor="rgba(214,39,40,0.15)",
            hovertemplate="x = %{x:.2f} m<br>V = %{y:.2f} kN<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.update_xaxes(title_text="Posição x [m]", row=2, col=1)
    fig.update_yaxes(title_text="M [kN·m]", row=1, col=1)
    fig.update_yaxes(title_text="V [kN]", row=2, col=1)
    fig.update_layout(
        title=f"Diagramas — {titulo}",
        height=620,
        showlegend=False,
        hovermode="x unified",
        margin=dict(l=60, r=30, t=80, b=60),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_memoria(L, q, b, h, descricao, M_max, V_max, r):
    texto = montar_memoria(L, q, b, h, descricao, M_max, V_max, r)
    st.markdown(texto)
    st.divider()
    st.markdown(
        "**Markdown bruto** (use o botão de copiar do bloco abaixo "
        "para colar em outra IA e pedir auditoria):"
    )
    st.code(texto, language="markdown")


def main():
    st.set_page_config(page_title="Viga Biapoiada V2", page_icon="🏗️", layout="wide")
    st.title("🏗️ Calculadora de Viga Biapoiada — V2")
    st.write(
        "Carga distribuída uniforme · Dimensionamento à flexão simples · "
        "Concreto C30 · Aço CA-50 · NBR 6118"
    )

    # Entradas — sidebar
    with st.sidebar:
        st.header("Entradas")
        L = st.number_input(
            "Vão L (m)", min_value=1.0, max_value=20.0, value=5.0, step=0.1,
            help="Comprimento do vão entre apoios (1,0 a 20,0 m)",
        )
        q = st.number_input(
            "Carga distribuída q (kN/m)",
            min_value=0.5, max_value=100.0, value=10.0, step=0.5,
            help="Carga uniforme característica total (0,5 a 100 kN/m)",
        )
        b = st.number_input(
            "Largura b (cm)", min_value=12, max_value=40, value=14, step=1,
            help="Largura da seção retangular (12 a 40 cm)",
        )
        h = st.number_input(
            "Altura h (cm)", min_value=30, max_value=100, value=50, step=1,
            help="Altura da seção retangular (30 a 100 cm)",
        )
        descricao = st.text_input("Descrição (opcional)", value="V1")

        st.divider()
        st.caption(
            "Parâmetros fixos: C30 · CA-50 · cobrimento 30 mm · "
            "Ø_estribo 5,0 mm · Ø_long 12,5 mm · γf=1,4 · γc=1,4 · γs=1,15"
        )

    # Cálculos
    M_max, V_max = calcular_esforcos(float(L), float(q))
    r = dimensionar_armadura(float(b), float(h), M_max)

    # 4 abas
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Resultados", "📋 Tabela Pandas", "📈 Diagramas", "📄 Memória"]
    )
    with tab1:
        render_resultados(M_max, V_max, r)
    with tab2:
        render_tabela(float(L), float(q), float(b), float(h),
                      descricao, M_max, V_max, r)
    with tab3:
        render_diagramas(float(L), float(q), descricao)
    with tab4:
        render_memoria(float(L), float(q), float(b), float(h),
                       descricao, M_max, V_max, r)

    st.divider()
    st.caption(f"⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()
