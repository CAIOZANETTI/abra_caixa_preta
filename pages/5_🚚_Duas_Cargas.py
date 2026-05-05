import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Duas Cargas Móveis",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 Duas Cargas Móveis — Trem de Cargas")
st.markdown(
    "Duas cargas com espaçamento fixo **d** percorrem a viga juntas — modelo de eixos "
    "de veículo. Observe o **duplo pico no diagrama M** e o envelope mais complexo "
    "que fundamenta o projeto de pontes (NBR 7188)."
)

# ── Parâmetros ───────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    L = st.slider("Comprimento  L  (m)", 4.0, 20.0, 10.0, 0.5)
    d_max = min(L - 0.5, 8.0)
    d = st.slider("Espaçamento entre eixos  d  (m)", 0.5, d_max,
                  min(2.0, d_max / 2), 0.25)

with c2:
    P1 = st.slider("Carga dianteira  P₁  (kN)", 10.0, 300.0, 80.0, 10.0)
    P2 = st.slider("Carga traseira   P₂  (kN)", 10.0, 300.0, 120.0, 10.0)

c3, c4 = st.columns([2, 1])
with c3:
    n_pos = st.slider("Número de posições (frames)", 30, 100, 50, 5)
with c4:
    mostrar_envelope = st.checkbox("Mostrar envelope  M máx", value=True)

# ── Cálculo ──────────────────────────────────────────────────────────────────
N = 300
x = np.linspace(0, L, N)

# a1 = posição da carga dianteira (P1); a2 = a1 + d (traseira, P2)
# Animação: P2 entra pela esquerda até P1 sair pela direita
a1_vals = np.linspace(-d + 0.01 * L, L - 0.01 * L, n_pos)
a2_vals = a1_vals + d


def calc_M(a1: float, a2: float) -> np.ndarray:
    M = np.zeros(N)
    for ai, Pi in [(a1, P1), (a2, P2)]:
        if 0.0 <= ai <= L:
            R_A_i = Pi * (L - ai) / L
            R_B_i = Pi * ai / L
            M += np.where(x <= ai, R_A_i * x, R_B_i * (L - x))
    return M


def calc_V_pts(a1: float, a2: float):
    """Função degrau do cortante com salto em cada carga sobre a viga."""
    eps = 1e-6 * L
    loads = sorted([(a, P) for a, P in [(a1, P1), (a2, P2)] if 0.0 <= a <= L])
    if not loads:
        return [0.0, L], [0.0, 0.0]
    R_A = sum(P * (L - a) / L for a, P in loads)
    xs = [0.0]
    ys = [R_A]
    V = R_A
    for a, P in loads:
        xs.extend([a, a + eps])
        ys.extend([V, V - P])
        V -= P
    xs.append(L)
    ys.append(V)
    return xs, ys


# ── Envelope ────────────────────────────────────────────────────────────────
if mostrar_envelope:
    env = np.zeros(N)
    for _a1 in np.linspace(-d, L, 500):
        env = np.maximum(env, calc_M(_a1, _a1 + d))

# ── Figura ───────────────────────────────────────────────────────────────────
fig = make_subplots(
    rows=3,
    cols=1,
    row_heights=[0.18, 0.41, 0.41],
    shared_xaxes=True,
    subplot_titles=[
        "Esquema da viga",
        "Momento Fletor  M(x)  [kN·m]",
        "Cortante  V(x)  [kN]",
    ],
    vertical_spacing=0.06,
)

M_scale = (P1 + P2) * L / 4
V_scale = P1 + P2
BEAM_H = 0.65

# ── Traços estáticos ─────────────────────────────────────────────────────────
# 0: viga
fig.add_trace(
    go.Scatter(x=[0, L], y=[0, 0], mode="lines",
               line=dict(color="#2c2c2c", width=8), showlegend=False),
    row=1, col=1,
)
# 1: apoio esquerdo
fig.add_trace(
    go.Scatter(x=[-0.18, 0, 0.18, -0.18], y=[-0.38, 0, -0.38, -0.38],
               mode="lines", fill="toself", fillcolor="#666",
               line=dict(color="#666", width=1), showlegend=False),
    row=1, col=1,
)
# 2: apoio direito
fig.add_trace(
    go.Scatter(x=[L - 0.18, L, L + 0.18, L - 0.18], y=[-0.38, 0, -0.38, -0.38],
               mode="lines", fill="toself", fillcolor="#666",
               line=dict(color="#666", width=1), showlegend=False),
    row=1, col=1,
)
# 3: zero line M
fig.add_trace(
    go.Scatter(x=[0, L], y=[0, 0], mode="lines",
               line=dict(color="#ccc", width=1, dash="dot"), showlegend=False),
    row=2, col=1,
)
# 4: zero line V
fig.add_trace(
    go.Scatter(x=[0, L], y=[0, 0], mode="lines",
               line=dict(color="#bbb", width=1, dash="dot"), showlegend=False),
    row=3, col=1,
)

n_static = 5

# 5 (opcional): envelope
if mostrar_envelope:
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([x, x[::-1]]),
            y=np.concatenate([env, np.zeros(N)]),
            fill="toself",
            fillcolor="rgba(255,180,0,0.18)",
            line=dict(color="goldenrod", width=1.5, dash="dot"),
            name="Envelope  M máx",
            showlegend=True,
        ),
        row=2, col=1,
    )
    n_static += 1

idx_load1 = n_static        # seta P1 (dianteira)
idx_load2 = n_static + 1   # seta P2 (traseira)
idx_M     = n_static + 2   # diagrama M
idx_V     = n_static + 3   # diagrama V

# ── Estado inicial ───────────────────────────────────────────────────────────
a1_0, a2_0 = a1_vals[0], a2_vals[0]
M0 = calc_M(a1_0, a2_0)
xv0, Vv0 = calc_V_pts(a1_0, a2_0)

# P1 — carga dianteira (laranja)
fig.add_trace(
    go.Scatter(
        x=[a1_0, a1_0], y=[BEAM_H, 0.04],
        mode="lines+markers",
        marker=dict(symbol=["triangle-down", "circle"], size=[16, 0], color="darkorange"),
        line=dict(color="darkorange", width=3),
        name=f"P₁ = {P1:.0f} kN  (dianteira)",
        showlegend=True,
    ),
    row=1, col=1,
)
# P2 — carga traseira (vermelho)
fig.add_trace(
    go.Scatter(
        x=[a2_0, a2_0], y=[BEAM_H, 0.04],
        mode="lines+markers",
        marker=dict(symbol=["triangle-down", "circle"], size=[16, 0], color="crimson"),
        line=dict(color="crimson", width=3),
        name=f"P₂ = {P2:.0f} kN  (traseira)",
        showlegend=True,
    ),
    row=1, col=1,
)
# M(x)
fig.add_trace(
    go.Scatter(
        x=x, y=M0,
        fill="tozeroy",
        fillcolor="rgba(30,100,255,0.22)",
        line=dict(color="royalblue", width=2),
        name="M(x)",
        showlegend=True,
    ),
    row=2, col=1,
)
# V(x)
fig.add_trace(
    go.Scatter(
        x=xv0, y=Vv0,
        fill="tozeroy",
        fillcolor="rgba(200,40,40,0.22)",
        line=dict(color="crimson", width=2),
        name="V(x)",
        showlegend=True,
    ),
    row=3, col=1,
)

# ── Frames de animação ───────────────────────────────────────────────────────
frames = []
for i, (a1, a2) in enumerate(zip(a1_vals, a2_vals)):
    M = calc_M(a1, a2)
    xv, Vv = calc_V_pts(a1, a2)
    frames.append(
        go.Frame(
            data=[
                go.Scatter(
                    x=[a1, a1], y=[BEAM_H, 0.04],
                    mode="lines+markers",
                    marker=dict(symbol=["triangle-down", "circle"], size=[16, 0],
                                color="darkorange"),
                    line=dict(color="darkorange", width=3),
                ),
                go.Scatter(
                    x=[a2, a2], y=[BEAM_H, 0.04],
                    mode="lines+markers",
                    marker=dict(symbol=["triangle-down", "circle"], size=[16, 0],
                                color="crimson"),
                    line=dict(color="crimson", width=3),
                ),
                go.Scatter(
                    x=x, y=M,
                    fill="tozeroy",
                    fillcolor="rgba(30,100,255,0.22)",
                    line=dict(color="royalblue", width=2),
                ),
                go.Scatter(
                    x=xv, y=Vv,
                    fill="tozeroy",
                    fillcolor="rgba(200,40,40,0.22)",
                    line=dict(color="crimson", width=2),
                ),
            ],
            traces=[idx_load1, idx_load2, idx_M, idx_V],
            name=str(i),
        )
    )

fig.frames = frames

# ── Slider de posição ────────────────────────────────────────────────────────
slider_steps = [
    dict(
        args=[[str(i)], dict(frame=dict(duration=0, redraw=True), mode="immediate")],
        label=f"{a1:.1f}",
        method="animate",
    )
    for i, a1 in enumerate(a1_vals)
]

# ── Layout ───────────────────────────────────────────────────────────────────
fig.update_layout(
    height=700,
    showlegend=True,
    legend=dict(orientation="h", y=-0.16, x=0.5, xanchor="center", font=dict(size=13)),
    updatemenus=[
        dict(
            type="buttons",
            showactive=False,
            x=0.01, y=1.10, xanchor="left",
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[
                        None,
                        dict(frame=dict(duration=75, redraw=True),
                             fromcurrent=True, mode="immediate"),
                    ],
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")],
                ),
            ],
        )
    ],
    sliders=[
        dict(
            steps=slider_steps,
            active=0,
            currentvalue=dict(
                prefix="a₁ = ", suffix=" m  (P₁)",
                font=dict(size=14, color="#444"),
                xanchor="center",
            ),
            x=0.03, len=0.94,
            pad=dict(t=45, b=5),
            bgcolor="#f5f5f5",
            tickcolor="#ddd",
        )
    ],
    margin=dict(t=55, b=110, l=65, r=20),
    plot_bgcolor="white",
    paper_bgcolor="white",
)

# ── Ranges dos eixos (abrangem trajetória completa das cargas) ────────────────
x_margin = d + 0.5
fig.update_xaxes(
    range=[-(x_margin), L + x_margin],
    showgrid=True, gridcolor="#efefef", showline=True, linecolor="#ddd",
)
fig.update_yaxes(row=1, col=1, range=[-0.65, BEAM_H + 0.2],
                 showticklabels=False, showgrid=False, zeroline=False)
fig.update_yaxes(row=2, col=1, range=[-M_scale * 0.08, M_scale * 1.20],
                 showgrid=True, gridcolor="#efefef",
                 zeroline=True, zerolinecolor="#bbb", zerolinewidth=1)
fig.update_yaxes(row=3, col=1, range=[-V_scale * 1.20, V_scale * 1.20],
                 showgrid=True, gridcolor="#efefef",
                 zeroline=True, zerolinecolor="#bbb", zerolinewidth=1)
fig.update_xaxes(title_text="x  (m)", row=3, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── Resultados para posição manual ───────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Resultados para posição escolhida")

a1_tab = st.slider(
    "Posição da carga dianteira  a₁  (m)",
    min_value=round(-d + 0.01, 2),
    max_value=round(L - 0.01, 2),
    value=round((L - d) / 2, 2),
    step=round(L / 100, 2),
)
a2_tab = a1_tab + d

loads_tab = [(a, P) for a, P in [(a1_tab, P1), (a2_tab, P2)] if 0.0 <= a <= L]
R_A_tab = sum(P * (L - a) / L for a, P in loads_tab)
R_B_tab = sum(P * a / L for a, P in loads_tab)
M_tab = calc_M(a1_tab, a2_tab)
M_max_tab = float(M_tab.max())
x_Mmax_tab = float(x[M_tab.argmax()])

cargas_ativas = len(loads_tab)
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Cargas na viga", f"{cargas_ativas} de 2")
mc2.metric("Reação  R_A", f"{R_A_tab:.1f} kN")
mc3.metric("Reação  R_B", f"{R_B_tab:.1f} kN")
mc4.metric("M máx", f"{M_max_tab:.1f} kN·m")
mc5.metric("Posição  M máx", f"x = {x_Mmax_tab:.2f} m")

# ── Formulário ───────────────────────────────────────────────────────────────
with st.expander("📐 Formulário — superposição de duas cargas"):
    st.markdown("Para cada carga $P_i$ na posição $a_i$ sobre a viga:")
    st.latex(
        r"M_i(x) = \begin{cases}"
        r"P_i\,\dfrac{L-a_i}{L}\cdot x & x \le a_i \\"
        r"P_i\,\dfrac{a_i}{L}\cdot (L-x) & x > a_i"
        r"\end{cases}"
    )
    st.markdown("**Superposição** (apenas cargas com $0 \\le a_i \\le L$ contribuem):")
    st.latex(r"M(x) = \sum_{i} M_i(x)")
    st.latex(
        r"R_A = \sum_i P_i\,\frac{L-a_i}{L} \qquad"
        r"R_B = \sum_i P_i\,\frac{a_i}{L}"
    )
    st.markdown(
        "**Duas cargas na viga:** o diagrama M exibe **dois picos** — um sob cada eixo. "
        "O envelope (linha amarela) acumula o M máximo possível em cada seção para todas "
        "as posições do trem de cargas, conceito central da **NBR 7188** "
        "(cargas móveis em pontes rodoviárias e pedestres)."
    )
