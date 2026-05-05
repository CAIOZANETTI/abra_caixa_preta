"""
Material Bônus — Pórtico 3D.

Pórtico simples (1 vão · 1 andar) com bases bi-rotuladas, carga distribuída
uniforme na viga. É o passo seguinte da viga isolada do app principal:
quando você "fecha" a viga em pilares, surgem reações horizontais nos
apoios e momento nos cantos — efeito que não aparece na biapoiada.

Hipóteses
---------
• Estrutura plana (xz), simétrica.
• Apoios: rotulados (pinos) na base.
• Mesma rigidez à flexão EI em todos os membros (resultado independe de EI).
• Carga: q vertical uniforme, apenas na viga.
• Pequenos deslocamentos · viga axialmente rígida (sem sway).

Solução fechada (slope-deflection, simetria θ_C = −θ_B):

    M_canto  = q·L³ / [ 4 · (3L + 2H) ]            (mód. do momento no canto)
    M_meio   = q·L²/8 − M_canto                    (momento no meio do vão)
    H_reac   = M_canto / H                         (rea. horiz. inward)
    V_reac   = q·L / 2                             (rea. vertical)

Limites úteis para sanity:
    H → 0    ⇒  M_canto → qL²/12   (pilar curtinho ≈ engaste perfeito)
    H → ∞    ⇒  M_canto → 0        (pilar muito flexível ≈ biapoiada)
"""

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from calc_core import DISCLAIMER


# ---------------------------------------------------------------------------
# Dados e cálculo
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Portico:
    L: float = 6.0          # vão da viga [m]
    H: float = 3.0          # altura dos pilares [m]
    q: float = 20.0         # carga distribuída na viga [kN/m]
    b_pilar: float = 0.30   # lado da seção quadrada do pilar [m]
    b_viga: float = 0.25    # base da seção da viga [m]
    h_viga: float = 0.50    # altura da seção da viga [m]


def calcular(p: Portico) -> dict:
    L, H, q = p.L, p.H, p.q
    M_canto = q * L ** 3 / (4.0 * (3.0 * L + 2.0 * H))
    M_meio = q * L ** 2 / 8.0 - M_canto
    H_reac = M_canto / H
    V_reac = q * L / 2.0
    return {
        "M_canto_kNm": M_canto,
        "M_meio_kNm": M_meio,
        "V_max_viga_kN": V_reac,    # cortante máximo na viga = qL/2
        "V_pilar_kN": H_reac,       # cortante constante no pilar = H_reac
        "N_pilar_kN": V_reac,       # axial no pilar (compressão)
        "H_reac_kN": H_reac,
        "V_reac_kN": V_reac,
        "M_max_abs_kNm": max(M_canto, M_meio),
    }


def momento_viga(x: float, p: Portico, M_canto: float) -> float:
    """M(x) na viga, x medido do apoio esquerdo. Sinal: + sagging."""
    return -M_canto + p.q * x * (p.L - x) / 2.0


def cortante_viga(x: float, p: Portico) -> float:
    return p.q * p.L / 2.0 - p.q * x


# ---------------------------------------------------------------------------
# Construção dos meshes 3D
# ---------------------------------------------------------------------------
def _box_mesh(corners_front, corners_back, intensities_front, intensities_back):
    """
    Constrói um box 3D dado 4 cantos da face frontal (z=z0 ou x=x0) e os 4
    cantos correspondentes da face traseira. Cada canto tem uma intensidade
    associada para colorir.

    Os 4 cantos seguem ordem ciclica (qualquer sentido coerente).

    Retorna: dict com x, y, z, i, j, k, intensity (listas).
    """
    pts = list(corners_front) + list(corners_back)
    intens = list(intensities_front) + list(intensities_back)

    vx = [p[0] for p in pts]
    vy = [p[1] for p in pts]
    vz = [p[2] for p in pts]

    # Indices: 0..3 frontal, 4..7 traseiro (mesma ordem cíclica).
    ii, jj, kk = [], [], []

    def quad(a, b, c, d):
        ii.extend([a, a]); jj.extend([b, c]); kk.extend([c, d])

    # Tampa frontal e traseira
    quad(0, 1, 2, 3)
    quad(4, 7, 6, 5)
    # Faces laterais (pares: frente i↔i+4)
    quad(0, 4, 5, 1)
    quad(1, 5, 6, 2)
    quad(2, 6, 7, 3)
    quad(3, 7, 4, 0)

    return dict(x=vx, y=vy, z=vz, i=ii, j=jj, k=kk, intensity=intens)


def _segmentos_pilar(x_centro: float, p: Portico, res: dict,
                     n_seg: int, modo: str):
    """Pilar (eixo z) subdividido em n_seg trechos.
    modo='M': M(z) = (z/H)·M_canto (linear, 0 na base → M_canto no topo).
    modo='V': cortante constante = H_reac em toda a altura."""
    bp = p.b_pilar
    H = p.H
    M_canto = res["M_canto_kNm"]
    V_pilar = res["V_pilar_kN"]

    vx, vy, vz, ii, jj, kk, intens = [], [], [], [], [], [], []
    base = 0
    z_pts = np.linspace(0.0, H + p.h_viga, n_seg + 1)

    # Cada seção tem 4 vértices: cantos do quadrado de lado bp em torno de x_centro,y=0.
    for k_sec, z in enumerate(z_pts):
        for (dx, dy) in [(-bp / 2, -bp / 2), (+bp / 2, -bp / 2),
                         (+bp / 2, +bp / 2), (-bp / 2, +bp / 2)]:
            vx.append(x_centro + dx)
            vy.append(0.0 + dy)
            vz.append(float(z))
            if modo == "V":
                intens.append(abs(V_pilar))
            else:
                z_clip = min(z, H)
                intens.append(abs(M_canto) * (z_clip / H if H > 0 else 1.0))

    def quad(a, b, c, d):
        ii.extend([a, a]); jj.extend([b, c]); kk.extend([c, d])

    # Tampas: base (k_sec=0) e topo (k_sec=n_seg)
    quad(0, 1, 2, 3)
    top = 4 * n_seg
    quad(top + 0, top + 3, top + 2, top + 1)
    # Faces laterais entre seções
    for s in range(n_seg):
        a = 4 * s
        b = 4 * (s + 1)
        quad(a + 0, b + 0, b + 1, a + 1)
        quad(a + 1, b + 1, b + 2, a + 2)
        quad(a + 2, b + 2, b + 3, a + 3)
        quad(a + 3, b + 3, b + 0, a + 0)

    return dict(x=vx, y=vy, z=vz, i=ii, j=jj, k=kk, intensity=intens)


def _segmentos_viga(p: Portico, res: dict, n_seg: int, modo: str):
    """Viga (eixo x) subdividida em n_seg trechos. Centro da seção em
    z = H + h_viga/2 (apoiada no topo dos pilares)."""
    L, H = p.L, p.H
    bv, hv = p.b_viga, p.h_viga
    M_canto = res["M_canto_kNm"]

    vx, vy, vz, ii, jj, kk, intens = [], [], [], [], [], [], []
    x_pts = np.linspace(0.0, L, n_seg + 1)
    z_centro = H + hv / 2.0

    # Cada seção: 4 cantos (em y, z) em torno de (0, z_centro).
    for x in x_pts:
        if modo == "V":
            val = abs(cortante_viga(float(x), p))
        else:
            val = abs(momento_viga(float(x), p, M_canto))
        for (dy, dz) in [(-bv / 2, -hv / 2), (+bv / 2, -hv / 2),
                         (+bv / 2, +hv / 2), (-bv / 2, +hv / 2)]:
            vx.append(float(x))
            vy.append(0.0 + dy)
            vz.append(z_centro + dz)
            intens.append(val)

    def quad(a, b, c, d):
        ii.extend([a, a]); jj.extend([b, c]); kk.extend([c, d])

    quad(0, 1, 2, 3)
    top = 4 * n_seg
    quad(top + 0, top + 3, top + 2, top + 1)
    for s in range(n_seg):
        a = 4 * s
        b = 4 * (s + 1)
        quad(a + 0, b + 0, b + 1, a + 1)
        quad(a + 1, b + 1, b + 2, a + 2)
        quad(a + 2, b + 2, b + 3, a + 3)
        quad(a + 3, b + 3, b + 0, a + 0)

    return dict(x=vx, y=vy, z=vz, i=ii, j=jj, k=kk, intensity=intens)


def _construir_apoios(p: Portico):
    """Cones cinza embaixo das bases (representando rótulas)."""
    bp = p.b_pilar
    altura = 0.20
    raio = bp / 2 * 1.3

    vx, vy, vz, ii, jj, kk = [], [], [], [], [], []

    for x_a in (0.0, p.L):
        base = len(vx)
        # Vértice superior (toca base do pilar)
        vx.append(x_a); vy.append(0.0); vz.append(0.0)
        # 8 vértices na base inferior (octógono)
        n_lat = 8
        for k in range(n_lat):
            ang = 2 * np.pi * k / n_lat
            vx.append(x_a + raio * np.cos(ang))
            vy.append(raio * np.sin(ang))
            vz.append(-altura)

        # Triângulos das laterais (do topo até cada par de vértices da base)
        for k in range(n_lat):
            a = base + 1 + k
            b = base + 1 + (k + 1) % n_lat
            ii.append(base); jj.append(a); kk.append(b)

    return dict(x=vx, y=vy, z=vz, i=ii, j=jj, k=kk)


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------
COR_APOIO = "#777777"


def construir_fig_3d(p: Portico, res: dict, modo: str = "M") -> go.Figure:
    """modo='M' colore por |M(x,z)|; modo='V' colore por |V(x,z)|."""
    n_seg = 16

    if modo == "V":
        # cmax = maior |V| da estrutura (geralmente qL/2 na viga, > V do pilar)
        cmax = max(res["V_max_viga_kN"], res["V_pilar_kN"])
        unidade, simbolo = "kN", "|V|"
    else:
        cmax = res["M_max_abs_kNm"]
        unidade, simbolo = "kN·m", "|M|"

    fig = go.Figure()

    coletas = [
        ("Pilar esquerdo", _segmentos_pilar(0.0, p, res, n_seg, modo)),
        ("Pilar direito", _segmentos_pilar(p.L, p, res, n_seg, modo)),
        ("Viga", _segmentos_viga(p, res, n_seg, modo)),
    ]
    for idx, (nome, m) in enumerate(coletas):
        fig.add_trace(go.Mesh3d(
            **m,
            colorscale="RdYlGn_r",
            cmin=0.0, cmax=max(cmax, 1e-6),
            showscale=(idx == 0),
            colorbar=dict(title=dict(text=f"{simbolo}<br>({unidade})",
                                     side="right"),
                          x=1.02, len=0.7, thickness=14) if idx == 0 else None,
            flatshading=False,
            opacity=1.0,
            lighting=dict(ambient=0.65, diffuse=0.75, specular=0.1),
            hovertemplate=f"{simbolo} = %{{intensity:.2f}} {unidade}"
                          f"<extra>{nome}</extra>",
            name=nome,
        ))

    # Apoios
    apoios = _construir_apoios(p)
    fig.add_trace(go.Mesh3d(
        **apoios,
        color=COR_APOIO,
        opacity=0.9,
        flatshading=True,
        showscale=False,
        hoverinfo="skip",
        name="Apoios",
    ))

    rotulo_modo = ("Momento fletor |M|" if modo == "M"
                   else "Esforço cortante |V|")
    titulo = (f"Pórtico bi-rotulado · {rotulo_modo} — "
              f"L={p.L:.1f} m · H={p.H:.1f} m · q={p.q:.0f} kN/m  |  "
              f"M_canto = {res['M_canto_kNm']:.1f} kN·m · "
              f"V_max = {res['V_max_viga_kN']:.1f} kN")
    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center", font=dict(size=13)),
        scene=dict(
            xaxis=dict(title="x (m)", backgroundcolor="white"),
            yaxis=dict(title="y (m)", backgroundcolor="white"),
            zaxis=dict(title="z (m) — altura", backgroundcolor="white"),
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=-1.6, z=0.7),
                        projection=dict(type="perspective")),
        ),
        height=620,
        margin=dict(l=10, r=10, t=70, b=10),
        paper_bgcolor="white",
        legend=dict(x=0.0, y=1.0, bgcolor="rgba(255,255,255,0.7)"),
    )
    return fig


def construir_fig_diagramas(p: Portico, res: dict) -> go.Figure:
    """Diagramas M(x) e V(x) ao longo da viga + M(z) ao longo do pilar."""
    from plotly.subplots import make_subplots

    M_canto = res["M_canto_kNm"]
    x = np.linspace(0.0, p.L, 121)
    M_v = np.array([momento_viga(xi, p, M_canto) for xi in x])
    V_v = np.array([cortante_viga(xi, p) for xi in x])

    z = np.linspace(0.0, p.H, 31)
    M_p = (z / p.H) * M_canto if p.H > 0 else np.zeros_like(z)

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "M(x) na viga [kN·m]  (negativo = hogging nos cantos)",
            "V(x) na viga [kN]",
            "M(z) no pilar [kN·m]",
        ),
        column_widths=[0.42, 0.30, 0.28],
        horizontal_spacing=0.08,
    )
    fig.add_trace(
        go.Scatter(x=x, y=M_v, mode="lines",
                   line=dict(color="#1f77b4", width=2.5),
                   fill="tozeroy",
                   fillcolor="rgba(31,119,180,0.15)",
                   hovertemplate="x = %{x:.2f} m<br>M = %{y:.2f} kN·m<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=x, y=V_v, mode="lines",
                   line=dict(color="#d62728", width=2.5),
                   fill="tozeroy",
                   fillcolor="rgba(214,39,40,0.15)",
                   hovertemplate="x = %{x:.2f} m<br>V = %{y:.2f} kN<extra></extra>"),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(x=M_p, y=z, mode="lines",
                   line=dict(color="#2ca02c", width=2.5),
                   fill="tozerox",
                   fillcolor="rgba(44,160,44,0.15)",
                   hovertemplate="z = %{y:.2f} m<br>M = %{x:.2f} kN·m<extra></extra>"),
        row=1, col=3,
    )
    fig.update_xaxes(title_text="x (m)", row=1, col=1)
    fig.update_xaxes(title_text="x (m)", row=1, col=2)
    fig.update_xaxes(title_text="M (kN·m)", row=1, col=3)
    fig.update_yaxes(title_text="M (kN·m)", row=1, col=1)
    fig.update_yaxes(title_text="V (kN)", row=1, col=2)
    fig.update_yaxes(title_text="z — altura (m)", row=1, col=3)
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(l=60, r=30, t=60, b=50),
    )
    return fig


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_3d_tab(p: Portico, res: dict):
    escolha = st.radio(
        "Esforço colorido na estrutura:",
        ("Momento fletor |M|", "Cortante |V|"),
        horizontal=True,
        key="modo_3d",
    )
    modo = "V" if "Cortante" in escolha else "M"

    fig = construir_fig_3d(p, res, modo=modo)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("M no canto", f"{res['M_canto_kNm']:.1f} kN·m",
              help="Momento (hogging) no encontro viga–pilar.")
    c2.metric("M no meio do vão", f"{res['M_meio_kNm']:.1f} kN·m",
              help="Momento (sagging) no centro da viga.")
    c3.metric("Reação H", f"{res['H_reac_kN']:.1f} kN",
              help="Reação horizontal nos apoios — empurra a base "
                   "para dentro do pórtico (não existe na viga biapoiada!).")
    c4.metric("Reação V", f"{res['V_reac_kN']:.1f} kN",
              help="Reação vertical em cada apoio = qL/2.")

    if modo == "M":
        st.info(
            "🎨 |M| é zero na base do pilar (rótula) e cresce linearmente até "
            "o canto. Na viga, o módulo é alto nos cantos (hogging), cai a "
            "zero nos pontos onde M troca de sinal e volta a subir no meio "
            "do vão (sagging). ↻ Arraste para rotacionar · 🔍 Scroll para zoom."
        )
    else:
        st.info(
            f"🎨 |V| na viga é máximo nos apoios (qL/2 = "
            f"{res['V_max_viga_kN']:.0f} kN) e zero no meio do vão. Nos "
            f"pilares o cortante é constante e bem menor "
            f"({res['V_pilar_kN']:.1f} kN = M_canto/H) — é exatamente a "
            "reação horizontal do apoio. Por isso o pilar "
            "aparece quase verde uniforme: o esforço dele é pequeno "
            "comparado ao da viga."
        )


def render_diagramas_tab(p: Portico, res: dict):
    fig = construir_fig_diagramas(p, res)
    st.plotly_chart(fig, use_container_width=True)

    M_meio = res["M_meio_kNm"]
    M_canto = res["M_canto_kNm"]
    M_biapoiada = p.q * p.L ** 2 / 8.0
    reducao = (1.0 - M_meio / M_biapoiada) * 100 if M_biapoiada > 0 else 0.0

    st.markdown(
        f"""
**Comparação com a viga biapoiada**

Se a viga estivesse simplesmente apoiada (sem pilares ligados rigidamente):

- M_max_biapoiada = q·L²/8 = **{M_biapoiada:.1f} kN·m**

No pórtico, parte desse momento "vaza" para os pilares como momento no canto:

- M_meio do pórtico = **{M_meio:.1f} kN·m**  ⇒  **{reducao:.0f}% menor** que a biapoiada.
- Em troca, surgem **{M_canto:.1f} kN·m** nos cantos (que a biapoiada não tem).

Quanto mais altos forem os pilares (H grande), mais o pórtico se aproxima
da biapoiada (M_canto → 0). Quanto mais curtos, mais se aproxima da viga
bi-engastada (M_canto → qL²/12).
"""
    )


def render_metodo_tab(p: Portico, res: dict):
    st.subheader("Método dos deslocamentos (slope-deflection) com simetria")
    st.markdown(
        r"""
A estrutura é **1× hiperestática**. Como ela é simétrica e o carregamento
também (q vertical uniforme), por simetria $\theta_C = -\theta_B$ — só
sobra uma incógnita: $\theta_B$ (rotação no canto).

**Equações de cada barra** (nó B):

$$M_{BA} = \frac{3EI}{H}\theta_B \qquad\text{(pilar AB, far-end pinned)}$$

$$M_{BC} = \frac{4EI}{L}\theta_B + \frac{2EI}{L}\theta_C - \frac{qL^2}{12}
        = \frac{2EI}{L}\theta_B - \frac{qL^2}{12}$$

**Equilíbrio em B** ($M_{BA} + M_{BC} = 0$):

$$\theta_B \left(\frac{3EI}{H} + \frac{2EI}{L}\right) = \frac{qL^2}{12}
\quad\Rightarrow\quad
\theta_B = \frac{qL^3 H}{12\,EI(3L + 2H)}$$

Substituindo:

$$\boxed{\;|M_{\text{canto}}| = \frac{qL^3}{4\,(3L + 2H)}\;}$$

**Repare**: o resultado **não depende de EI** — sai do quociente. Vale
para qualquer concreto, qualquer aço, contanto que pilares e viga tenham
a mesma rigidez à flexão.
"""
    )

    st.subheader("Tabela de esforços e reações")
    import pandas as pd
    L, H = p.L, p.H
    df = pd.DataFrame([
        {"Grandeza": "M no canto (hogging)", "Valor": f"{res['M_canto_kNm']:.2f} kN·m",
         "Fórmula": "qL³ / [4(3L+2H)]"},
        {"Grandeza": "M no meio do vão (sagging)", "Valor": f"{res['M_meio_kNm']:.2f} kN·m",
         "Fórmula": "qL²/8 − M_canto"},
        {"Grandeza": "Cortante máx. na viga", "Valor": f"{res['V_max_viga_kN']:.2f} kN",
         "Fórmula": "qL/2"},
        {"Grandeza": "Cortante no pilar (constante)", "Valor": f"{res['V_pilar_kN']:.2f} kN",
         "Fórmula": "M_canto / H"},
        {"Grandeza": "Axial no pilar (compressão)", "Valor": f"{res['N_pilar_kN']:.2f} kN",
         "Fórmula": "qL/2"},
        {"Grandeza": "Reação horizontal (inward)", "Valor": f"{res['H_reac_kN']:.2f} kN",
         "Fórmula": "M_canto / H"},
        {"Grandeza": "Reação vertical", "Valor": f"{res['V_reac_kN']:.2f} kN",
         "Fórmula": "qL/2"},
    ])
    st.dataframe(df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Pórtico 3D — Material Bônus",
        page_icon="🏛️",
        layout="wide",
    )
    st.title("🏛️ Material Bônus — Pórtico 3D")
    st.write(
        "**Próximo passo do curso**: a viga biapoiada do app principal "
        "agora vira um **pórtico** — duas colunas rigidamente ligadas a uma "
        "viga. Surgem dois efeitos novos que a viga isolada não tem: "
        "**reação horizontal nos apoios** e **momento no canto**."
    )

    with st.sidebar:
        st.header("Geometria")
        L = st.number_input("Vão da viga L (m)", min_value=2.0, max_value=20.0,
                            value=6.0, step=0.5)
        H = st.number_input("Altura dos pilares H (m)", min_value=1.0,
                            max_value=15.0, value=3.0, step=0.5)

        st.header("Carga")
        q = st.number_input("Carga distribuída q (kN/m)",
                            min_value=1.0, max_value=200.0, value=20.0, step=1.0)

        with st.expander("Seções (apenas visual)"):
            b_pilar = st.number_input("Lado do pilar (m)", 0.15, 0.80,
                                      0.30, step=0.05)
            b_viga = st.number_input("Base da viga (m)", 0.10, 0.60,
                                     0.25, step=0.05)
            h_viga = st.number_input("Altura da viga (m)", 0.20, 1.20,
                                     0.50, step=0.05)

    p = Portico(L=L, H=H, q=q,
                b_pilar=b_pilar, b_viga=b_viga, h_viga=h_viga)
    res = calcular(p)

    tab1, tab2, tab3 = st.tabs([
        "🏛️ Pórtico 3D",
        "📊 Diagramas M e V",
        "📐 Método e Tabela",
    ])
    with tab1:
        render_3d_tab(p, res)
    with tab2:
        render_diagramas_tab(p, res)
    with tab3:
        render_metodo_tab(p, res)

    st.divider()
    st.caption(f"⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()
