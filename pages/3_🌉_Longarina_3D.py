"""
Material Bônus — Longarina de Ponte em 3D.

Mostra ao aluno como a viga retangular do app principal evolui para uma seção
real de longarina (T com mesa inferior), calcula propriedades geométricas da
seção composta (A, ȳ, I, W) e extruda a seção ao longo do vão em 3D.

Esta página é puramente educacional: nenhuma alteração no código das outras
páginas (1_app principal e 2_Cálculo em Lote) é feita aqui.
"""

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from calc_core import DISCLAIMER


# ---------------------------------------------------------------------------
# Geometria paramétrica da seção
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SecaoLongarina:
    """Dimensões em centímetros. A seção é simétrica em torno do eixo vertical.

    Decomposição em 5 peças (de baixo para cima):
        1. Mesa inferior (retângulo bf_inf × tf_inf)
        2. Chanfro inferior (trapézio: b_alma → bf_inf, altura h_chanf_inf)
        3. Alma (retângulo b_alma × h_alma)
        4. Chanfro superior (trapézio: b_alma → bf_sup, altura h_chanf_sup)
        5. Mesa superior (retângulo bf_sup × tf_sup)
    """

    bf_sup: float = 90.0
    tf_sup: float = 12.0
    h_chanf_sup: float = 16.0  # combina os 6+10 do desenho original
    b_alma: float = 20.0
    h_alma: float = 110.0
    h_chanf_inf: float = 25.0
    bf_inf: float = 60.0
    tf_inf: float = 20.0

    @property
    def h_total(self) -> float:
        return (self.tf_inf + self.h_chanf_inf + self.h_alma
                + self.h_chanf_sup + self.tf_sup)


def _trapezio(w_top: float, w_bot: float, h: float, y_bot: float):
    """Propriedades de um trapézio simétrico com bases paralelas ao eixo y.

    Retorna (A, ȳ_global, I_local) onde:
        A         — área
        ȳ_global  — ordenada do CG do trapézio medida a partir de y=0
        I_local   — momento de inércia em torno do eixo horizontal que passa
                    pelo CG do trapézio (Iz local).
    """
    A = (w_top + w_bot) * h / 2.0
    # CG medido a partir da base inferior do trapézio (fórmula clássica):
    if (w_top + w_bot) > 0:
        y_local = h * (2.0 * w_top + w_bot) / (3.0 * (w_top + w_bot))
    else:
        y_local = h / 2.0
    # Iz local em torno do eixo horizontal pelo CG:
    # I = h³ (a² + 4ab + b²) / [36 (a+b)],   onde a = w_top, b = w_bot.
    if (w_top + w_bot) > 0:
        I_local = (h ** 3) * (w_top ** 2 + 4.0 * w_top * w_bot + w_bot ** 2) \
            / (36.0 * (w_top + w_bot))
    else:
        I_local = 0.0
    return A, y_bot + y_local, I_local


def _retangulo(w: float, h: float, y_bot: float):
    A = w * h
    y = y_bot + h / 2.0
    I_local = w * h ** 3 / 12.0
    return A, y, I_local


def calcular_propriedades(s: SecaoLongarina) -> dict:
    """Calcula A, ȳ (medido do bordo inferior), I e módulos resistentes."""
    pecas = []
    y_bot = 0.0

    A, y, Il = _retangulo(s.bf_inf, s.tf_inf, y_bot)
    pecas.append(("Mesa inferior", A, y, Il))
    y_bot += s.tf_inf

    A, y, Il = _trapezio(s.b_alma, s.bf_inf, s.h_chanf_inf, y_bot)
    pecas.append(("Chanfro inferior", A, y, Il))
    y_bot += s.h_chanf_inf

    A, y, Il = _retangulo(s.b_alma, s.h_alma, y_bot)
    pecas.append(("Alma", A, y, Il))
    y_bot += s.h_alma

    A, y, Il = _trapezio(s.bf_sup, s.b_alma, s.h_chanf_sup, y_bot)
    pecas.append(("Chanfro superior", A, y, Il))
    y_bot += s.h_chanf_sup

    A, y, Il = _retangulo(s.bf_sup, s.tf_sup, y_bot)
    pecas.append(("Mesa superior", A, y, Il))

    A_total = sum(p[1] for p in pecas)
    y_cg = sum(p[1] * p[2] for p in pecas) / A_total
    # Steiner: I_total = Σ (I_local_i + A_i · d_i²)
    I_total = sum(p[3] + p[1] * (p[2] - y_cg) ** 2 for p in pecas)

    h = s.h_total
    W_inf = I_total / y_cg                # módulo resistente da fibra inferior
    W_sup = I_total / (h - y_cg)          # módulo resistente da fibra superior

    return {
        "pecas": pecas,
        "A_cm2": A_total,
        "y_cg_cm": y_cg,
        "I_cm4": I_total,
        "W_inf_cm3": W_inf,
        "W_sup_cm3": W_sup,
        "h_total_cm": h,
    }


def poligono_secao(s: SecaoLongarina):
    """Vértices (x, y) do contorno da seção, em cm, no sentido horário a partir
    do canto superior direito. Origem no centro da base inferior."""
    pts = [
        (s.bf_sup / 2,  s.h_total),
        (s.bf_sup / 2,  s.h_total - s.tf_sup),
        (s.b_alma / 2,  s.h_total - s.tf_sup - s.h_chanf_sup),
        (s.b_alma / 2,  s.tf_inf + s.h_chanf_inf),
        (s.bf_inf / 2,  s.tf_inf),
        (s.bf_inf / 2,  0.0),
        (-s.bf_inf / 2, 0.0),
        (-s.bf_inf / 2, s.tf_inf),
        (-s.b_alma / 2, s.tf_inf + s.h_chanf_inf),
        (-s.b_alma / 2, s.h_total - s.tf_sup - s.h_chanf_sup),
        (-s.bf_sup / 2, s.h_total - s.tf_sup),
        (-s.bf_sup / 2, s.h_total),
    ]
    return pts


# ---------------------------------------------------------------------------
# Visualização 2D
# ---------------------------------------------------------------------------
def construir_fig_2d(s: SecaoLongarina, props: dict) -> go.Figure:
    pts = poligono_secao(s)
    xs = [p[0] for p in pts] + [pts[0][0]]
    ys = [p[1] for p in pts] + [pts[0][1]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines", fill="toself",
        line=dict(color="#0B1D35", width=2),
        fillcolor="rgba(11,29,53,0.10)",
        name="Seção",
        hoverinfo="skip",
    ))

    # Centroide
    y_cg = props["y_cg_cm"]
    fig.add_trace(go.Scatter(
        x=[-s.bf_sup / 2 - 5, s.bf_sup / 2 + 5],
        y=[y_cg, y_cg],
        mode="lines",
        line=dict(color="#D62728", width=1.5, dash="dash"),
        name=f"CG (ȳ = {y_cg:.1f} cm)",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[0], y=[y_cg],
        mode="markers+text",
        marker=dict(color="#D62728", size=10, symbol="x"),
        text=["CG"], textposition="middle right",
        textfont=dict(color="#D62728", size=11),
        showlegend=False,
        hovertemplate=f"CG: ȳ = {y_cg:.2f} cm<extra></extra>",
    ))

    fig.update_layout(
        title="Seção transversal (cm) — longarina de ponte",
        xaxis=dict(title="y (cm)", scaleanchor="y", scaleratio=1, zeroline=True),
        yaxis=dict(title="z (cm)", zeroline=True),
        height=520,
        showlegend=True,
        margin=dict(l=40, r=20, t=60, b=40),
        plot_bgcolor="white",
    )
    return fig


# ---------------------------------------------------------------------------
# Visualização 3D — extrusão da seção ao longo do vão
# ---------------------------------------------------------------------------
def _piece_mesh(w_top, w_bot, y_bot_local, h_piece, L, x_offset_arrays):
    """Gera vértices e triângulos de um prisma trapezoidal com seção
    (w_top em cima, w_bot embaixo, altura h_piece) extrudado em x ∈ [0, L].

    Os arrays vx, vy, vz, i_idx, j_idx, k_idx são apendados em x_offset_arrays
    (que carrega o offset corrente de vértices)."""
    vx, vy, vz, ii, jj, kk, base = x_offset_arrays
    y_top = y_bot_local + h_piece

    # 8 vértices do prisma
    pts = [
        # face frontal (x=0): cantos do trapézio (sentido horário olhando +x)
        (0.0,  w_top / 2.0,  y_top),    # 0
        (0.0,  w_bot / 2.0,  y_bot_local),  # 1
        (0.0, -w_bot / 2.0,  y_bot_local),  # 2
        (0.0, -w_top / 2.0,  y_top),    # 3
        # face traseira (x=L)
        (L,    w_top / 2.0,  y_top),    # 4
        (L,    w_bot / 2.0,  y_bot_local),  # 5
        (L,   -w_bot / 2.0,  y_bot_local),  # 6
        (L,   -w_top / 2.0,  y_top),    # 7
    ]
    for x, y, z in pts:
        vx.append(x); vy.append(y); vz.append(z)

    b = base[0]

    def quad(a, b_, c, d):
        """Quad (a,b,c,d) → 2 triângulos."""
        ii.extend([a, a]); jj.extend([b_, c]); kk.extend([c, d])

    # Tampas (frontal e traseira)
    quad(b + 0, b + 1, b + 2, b + 3)
    quad(b + 4, b + 7, b + 6, b + 5)
    # Faces laterais
    quad(b + 0, b + 4, b + 5, b + 1)   # +y
    quad(b + 1, b + 5, b + 6, b + 2)   # base
    quad(b + 2, b + 6, b + 7, b + 3)   # -y
    quad(b + 3, b + 7, b + 4, b + 0)   # topo

    base[0] += 8


def construir_fig_3d(s: SecaoLongarina, L_m: float, q_kN_m: float,
                     M_max_kNm: float) -> go.Figure:
    """Extruda a seção ao longo do vão e colore por |M(x)|."""
    L_cm = L_m * 100.0

    vx, vy, vz = [], [], []
    ii, jj, kk = [], [], []
    base = [0]

    # Em _piece_mesh, w_top é a largura na cota superior (y_bot_local + h)
    # e w_bot a largura na base (y_bot_local). Mesa→alma encolhe (chanfro
    # superior: w_top = bf_sup, w_bot = b_alma); alma→mesa expande (chanfro
    # inferior: w_top = b_alma, w_bot = bf_inf).
    pecas = [
        (s.bf_inf, s.bf_inf, 0.0, s.tf_inf),
        (s.b_alma, s.bf_inf, s.tf_inf, s.h_chanf_inf),
        (s.b_alma, s.b_alma, s.tf_inf + s.h_chanf_inf, s.h_alma),
        (s.bf_sup, s.b_alma,
         s.tf_inf + s.h_chanf_inf + s.h_alma, s.h_chanf_sup),
        (s.bf_sup, s.bf_sup, s.h_total - s.tf_sup, s.tf_sup),
    ]

    arrays = (vx, vy, vz, ii, jj, kk, base)
    for w_top, w_bot, y_bot_local, h_piece in pecas:
        _piece_mesh(w_top, w_bot, y_bot_local, h_piece, L_cm, arrays)

    # Intensidade: |M(x)| de viga biapoiada com q uniforme.
    # Como cada vértice tem coordenada x conhecida, mapeamos diretamente.
    M_max_local = max(M_max_kNm, 1e-6)
    intensidade = []
    for x in vx:
        x_m = x / 100.0
        M = q_kN_m * x_m * (L_m - x_m) / 2.0
        intensidade.append(abs(M))

    fig = go.Figure()
    fig.add_trace(go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=ii, j=jj, k=kk,
        intensity=intensidade,
        colorscale="RdYlGn_r",
        cmin=0.0, cmax=M_max_local,
        showscale=True,
        colorbar=dict(title=dict(text="|M(x)|<br>(kN·m)", side="right"),
                      x=1.02, len=0.7, thickness=14),
        flatshading=False,
        opacity=1.0,
        lighting=dict(ambient=0.65, diffuse=0.75, specular=0.1),
        hovertemplate="x = %{x:.0f} cm<br>|M| = %{intensity:.2f} kN·m<extra></extra>",
        name="Longarina",
    ))

    fig.update_layout(
        title=dict(
            text=(f"Longarina extrudada — vão L = {L_m:.1f} m | "
                  f"H = {s.h_total:.0f} cm | M_max = {M_max_kNm:.1f} kN·m"),
            x=0.5, xanchor="center", font=dict(size=14),
        ),
        scene=dict(
            xaxis=dict(title="x (cm) — vão", backgroundcolor="white"),
            yaxis=dict(title="y (cm) — largura", backgroundcolor="white"),
            zaxis=dict(title="z (cm) — altura", backgroundcolor="white"),
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.4, z=0.9),
                        projection=dict(type="perspective")),
        ),
        height=620,
        margin=dict(l=10, r=10, t=70, b=10),
        paper_bgcolor="white",
    )
    return fig


# ---------------------------------------------------------------------------
# Esforços e tensões
# ---------------------------------------------------------------------------
def construir_fig_tensoes(s: SecaoLongarina, props: dict,
                          M_kNm: float) -> go.Figure:
    """Plota a distribuição linear de tensões σ = M·(z - ȳ)/I sobre a altura
    da seção. Compressão (σ<0) à esquerda, tração (σ>0) à direita."""
    y_cg = props["y_cg_cm"]
    h = props["h_total_cm"]
    I_cm4 = props["I_cm4"]

    # Converte para unidades coerentes: M em kN·m → kN·cm; I em cm⁴; z em cm.
    # σ [kN/cm²] = M [kN·cm] · (z - ȳ) [cm] / I [cm⁴]
    # 1 kN/cm² = 10 MPa
    M_kNcm = M_kNm * 100.0

    z = np.linspace(0.0, h, 200)
    sigma_kNcm2 = -M_kNcm * (z - y_cg) / I_cm4   # compressão no topo (z>ȳ)
    sigma_MPa = sigma_kNcm2 * 10.0

    sigma_top = -M_kNcm * (h - y_cg) / I_cm4 * 10.0
    sigma_bot = -M_kNcm * (0.0 - y_cg) / I_cm4 * 10.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sigma_MPa, y=z, mode="lines",
        line=dict(color="#0B1D35", width=2.5),
        fill="tozerox",
        fillcolor="rgba(11,29,53,0.10)",
        name="σ(z)",
        hovertemplate="z = %{y:.1f} cm<br>σ = %{x:.2f} MPa<extra></extra>",
    ))
    fig.add_hline(y=y_cg, line=dict(color="#D62728", width=1, dash="dash"),
                  annotation_text=f"ȳ = {y_cg:.1f} cm",
                  annotation_position="top right")
    fig.add_vline(x=0.0, line=dict(color="#888", width=1))

    fig.update_layout(
        title=(f"Tensões normais σ(z) para M = {M_kNm:.1f} kN·m  "
               f"|  σ_topo = {sigma_top:.2f} MPa  ·  "
               f"σ_base = {sigma_bot:.2f} MPa"),
        xaxis=dict(title="σ (MPa)  — compressão (−) | tração (+)",
                   zeroline=True),
        yaxis=dict(title="z (cm) — altura medida do bordo inferior"),
        height=460,
        margin=dict(l=60, r=30, t=70, b=60),
        plot_bgcolor="white",
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_propriedades_tab(s: SecaoLongarina, props: dict):
    col_g, col_t = st.columns([1.1, 1])

    with col_g:
        fig2d = construir_fig_2d(s, props)
        st.plotly_chart(fig2d, use_container_width=True)

    with col_t:
        st.subheader("Propriedades geométricas")
        st.caption(
            "Seção decomposta em 5 peças. Cada uma contribui para A, ȳ e I "
            "(via Steiner)."
        )

        import pandas as pd
        df_pecas = pd.DataFrame(
            [{"Peça": nome,
              "A (cm²)": round(A, 1),
              "ȳ_peça (cm)": round(y, 2),
              "I_local (cm⁴)": round(Il, 0)}
             for (nome, A, y, Il) in props["pecas"]]
        )
        st.dataframe(df_pecas, hide_index=True, use_container_width=True)

        st.markdown("**Seção composta**")
        c1, c2 = st.columns(2)
        c1.metric("Área total A", f"{props['A_cm2']:.1f} cm²")
        c1.metric("Centroide ȳ", f"{props['y_cg_cm']:.2f} cm")
        c2.metric("Inércia I", f"{props['I_cm4']:.0f} cm⁴")
        c2.metric("Altura H", f"{props['h_total_cm']:.1f} cm")

        c3, c4 = st.columns(2)
        c3.metric("W_inf", f"{props['W_inf_cm3']:.0f} cm³",
                  help="Módulo resistente da fibra inferior (tração no positivo).")
        c4.metric("W_sup", f"{props['W_sup_cm3']:.0f} cm³",
                  help="Módulo resistente da fibra superior (compressão).")

        st.info(
            "💡 **Compare com a viga retangular do app principal**: lá I = b·h³/12 "
            "vale direto. Aqui a seção é assimétrica — o CG não fica no meio "
            "da altura, e os módulos resistentes superior e inferior são "
            "diferentes. É por isso que numa longarina protendida a mesa "
            "inferior costuma ser a região mais armada."
        )


def render_3d_tab(s: SecaoLongarina, L_m: float, q_kN_m: float):
    M_max = q_kN_m * L_m ** 2 / 8.0
    fig3d = construir_fig_3d(s, L_m, q_kN_m, M_max)
    st.plotly_chart(fig3d, use_container_width=True)
    st.info(
        "🎨 Cor mapeia |M(x)| ao longo do vão (verde nos apoios → vermelho no "
        "meio). A geometria 3D é a mesma seção da aba anterior, extrudada por "
        f"L = {L_m:.1f} m. ↻ Arraste para rotacionar · 🔍 Scroll para zoom · "
        "duplo-clique reseta a câmera."
    )


def render_tensoes_tab(s: SecaoLongarina, props: dict,
                       L_m: float, q_kN_m: float):
    M_max = q_kN_m * L_m ** 2 / 8.0
    V_max = q_kN_m * L_m / 2.0

    c1, c2 = st.columns(2)
    c1.metric("M_max = q·L²/8", f"{M_max:.2f} kN·m")
    c2.metric("V_max = q·L/2", f"{V_max:.2f} kN")

    fig_sigma = construir_fig_tensoes(s, props, M_max)
    st.plotly_chart(fig_sigma, use_container_width=True)

    st.markdown(
        f"""
**Fórmula da flexão de Navier**

$$\\sigma(z) = -\\dfrac{{M \\cdot (z - \\bar y)}}{{I}}$$

Para M = {M_max:.2f} kN·m e a seção atual (I = {props['I_cm4']:.0f} cm⁴,
ȳ = {props['y_cg_cm']:.2f} cm):

- Fibra superior (z = H): σ = −M / W_sup = **{-M_max * 100 / props['W_sup_cm3'] * 10:.2f} MPa** (compressão)
- Fibra inferior (z = 0): σ = +M / W_inf = **{+M_max * 100 / props['W_inf_cm3'] * 10:.2f} MPa** (tração)

Numa ponte real, o passo seguinte é checar se a tração na fibra inferior
ultrapassa a resistência à tração do concreto — em geral ultrapassa, e por
isso se usa **protensão** (cabo na mesa inferior comprime a seção e
"cancela" a tração).
"""
    )


def main():
    st.set_page_config(
        page_title="Longarina 3D — Material Bônus",
        page_icon="🌉",
        layout="wide",
    )
    st.title("🌉 Material Bônus — Longarina de Ponte em 3D")
    st.write(
        "**Próximo passo do curso**: a viga retangular vira uma seção real "
        "de longarina (T com mesa inferior). Você ajusta as dimensões na "
        "barra lateral, vê as propriedades geométricas da seção composta e "
        "a peça extrudada em 3D ao longo do vão."
    )

    with st.sidebar:
        st.header("Geometria da seção (cm)")
        st.caption("Defaults baseados em uma longarina típica de pré-moldado.")

        bf_sup = st.number_input("Mesa superior — largura b_f,sup",
                                 min_value=30.0, max_value=300.0,
                                 value=90.0, step=5.0)
        tf_sup = st.number_input("Mesa superior — espessura t_f,sup",
                                 min_value=5.0, max_value=40.0,
                                 value=12.0, step=1.0)
        h_chanf_sup = st.number_input("Chanfro superior — altura",
                                      min_value=0.0, max_value=60.0,
                                      value=16.0, step=1.0)
        b_alma = st.number_input("Alma — largura b_w",
                                 min_value=10.0, max_value=80.0,
                                 value=20.0, step=1.0)
        h_alma = st.number_input("Alma — altura h_alma",
                                 min_value=30.0, max_value=300.0,
                                 value=110.0, step=5.0)
        h_chanf_inf = st.number_input("Chanfro inferior — altura",
                                      min_value=0.0, max_value=60.0,
                                      value=25.0, step=1.0)
        bf_inf = st.number_input("Mesa inferior — largura b_f,inf",
                                 min_value=20.0, max_value=200.0,
                                 value=60.0, step=5.0)
        tf_inf = st.number_input("Mesa inferior — espessura t_f,inf",
                                 min_value=5.0, max_value=60.0,
                                 value=20.0, step=1.0)

        # Garantir consistência: bf_sup ≥ b_alma e bf_inf ≥ b_alma
        if bf_sup < b_alma or bf_inf < b_alma:
            st.error("As mesas devem ser ≥ que a largura da alma.")
            st.stop()

        st.divider()
        st.header("Vão e carga")
        L_m = st.number_input("Vão L (m)", min_value=5.0, max_value=60.0,
                              value=25.0, step=1.0)
        q = st.number_input("Carga distribuída q (kN/m)",
                            min_value=1.0, max_value=200.0,
                            value=30.0, step=1.0,
                            help="Carga uniforme equivalente ao peso próprio "
                                 "+ pavimento + sobrecarga (simplificação).")

    s = SecaoLongarina(
        bf_sup=bf_sup, tf_sup=tf_sup, h_chanf_sup=h_chanf_sup,
        b_alma=b_alma, h_alma=h_alma,
        h_chanf_inf=h_chanf_inf, bf_inf=bf_inf, tf_inf=tf_inf,
    )
    props = calcular_propriedades(s)

    tab1, tab2, tab3 = st.tabs([
        "📐 Seção & Propriedades",
        "🌉 Longarina 3D",
        "📊 Esforços & Tensões",
    ])
    with tab1:
        render_propriedades_tab(s, props)
    with tab2:
        render_3d_tab(s, L_m, q)
    with tab3:
        render_tensoes_tab(s, props, L_m, q)

    st.divider()
    st.caption(f"⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()
