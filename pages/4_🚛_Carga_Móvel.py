import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Carga Móvel",
    page_icon="🚛",
    layout="wide",
)

st.title("🚛 Carga Móvel — Diagramas Animados")
st.markdown(
    "Observe como **M(x)** e **V(x)** variam enquanto uma carga concentrada percorre "
    "a viga simplesmente apoiada. Clique **▶ Play** para animar."
)

# ── Parâmetros ──────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 3])
with c1:
    L = st.slider("Comprimento  L  (m)", 4.0, 16.0, 8.0, 0.5)
with c2:
    P = st.slider("Carga  P  (kN)", 10.0, 300.0, 100.0, 10.0)
with c3:
    n_pos = st.slider("Número de posições (frames)", 20, 80, 40, 5)
    mostrar_envelope = st.checkbox("Mostrar envelope  M máx", value=True)

# ── Funções de cálculo ───────────────────────────────────────────────────────
N = 300
x = np.linspace(0, L, N)
a_vals = np.linspace(0.02 * L, 0.98 * L, n_pos)


def m_vals(a: float) -> np.ndarray:
    R_A = P * (L - a) / L
    R_B = P * a / L
    return np.where(x <= a, R_A * x, R_B * (L - x))


def v_pts(a: float):
    """Step function para o cortante — 4 pontos com salto em x=a."""
    R_A = P * (L - a) / L
    R_B = P * a / L
    eps = 1e-6 * L
    return [0.0, a, a + eps, L], [R_A, R_A, -R_B, -R_B]


# ── Envelope ────────────────────────────────────────────────────────────────
if mostrar_envelope:
    env = np.zeros(N)
    for _a in np.linspace(0.01 * L, 0.99 * L, 400):
        env = np.maximum(env, m_vals(_a))

# ── Figura com subplots ──────────────────────────────────────────────────────
fig = make_subplots(
    rows=3,
    cols=1,
    row_heights=[0.18, 0.41, 0.41],
    shared_xaxes=True,
    subplot_titles=["Esquema da viga", "Momento Fletor  M(x)  [kN·m]", "Cortante  V(x)  [kN]"],
    vertical_spacing=0.06,
)

M_scale = P * L / 4   # momento máximo possível (carga no centro)
V_scale = P            # cortante máximo possível
BEAM_H = 0.65          # altura da seta de carga no painel superior

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
# 3: linha zero M
fig.add_trace(
    go.Scatter(x=[0, L], y=[0, 0], mode="lines",
               line=dict(color="#ccc", width=1, dash="dot"), showlegend=False),
    row=2, col=1,
)
# 4: linha zero V
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

idx_load = n_static
idx_M = n_static + 1
idx_V = n_static + 2

# ── Traços animados — estado inicial ─────────────────────────────────────────
a0 = a_vals[0]
M0 = m_vals(a0)
xv0, Vv0 = v_pts(a0)

# seta de carga
fig.add_trace(
    go.Scatter(
        x=[a0, a0], y=[BEAM_H, 0.04],
        mode="lines+markers",
        marker=dict(symbol=["triangle-down", "circle"], size=[16, 0], color="crimson"),
        line=dict(color="crimson", width=3),
        name="Carga  P",
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
for i, a in enumerate(a_vals):
    M = m_vals(a)
    xv, Vv = v_pts(a)
    frames.append(
        go.Frame(
            data=[
                go.Scatter(
                    x=[a, a], y=[BEAM_H, 0.04],
                    mode="lines+markers",
                    marker=dict(symbol=["triangle-down", "circle"], size=[16, 0], color="crimson"),
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
            traces=[idx_load, idx_M, idx_V],
            name=str(i),
        )
    )

fig.frames = frames

# ── Slider de posição ────────────────────────────────────────────────────────
slider_steps = [
    dict(
        args=[[str(i)], dict(frame=dict(duration=0, redraw=True), mode="immediate")],
        label=f"{a:.1f}",
        method="animate",
    )
    for i, a in enumerate(a_vals)
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
                prefix="a = ", suffix=" m",
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

# ── Ranges dos eixos (fixos para não mudar zoom) ─────────────────────────────
fig.update_xaxes(
    range=[-0.4, L + 0.4],
    showgrid=True, gridcolor="#efefef", gridwidth=1,
    showline=True, linecolor="#ddd",
)
fig.update_yaxes(
    row=1, col=1,
    range=[-0.65, BEAM_H + 0.2],
    showticklabels=False,
    showgrid=False,
    zeroline=False,
)
fig.update_yaxes(
    row=2, col=1,
    range=[-M_scale * 0.08, M_scale * 1.20],
    showgrid=True, gridcolor="#efefef",
    zeroline=True, zerolinecolor="#bbb", zerolinewidth=1,
)
fig.update_yaxes(
    row=3, col=1,
    range=[-V_scale * 1.20, V_scale * 1.20],
    showgrid=True, gridcolor="#efefef",
    zeroline=True, zerolinecolor="#bbb", zerolinewidth=1,
)
fig.update_xaxes(title_text="x  (m)", row=3, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── Resultados numéricos ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Resultados para posição escolhida")

a_tab = st.slider(
    "Posição da carga  a  (m)",
    min_value=round(0.01 * L, 2),
    max_value=round(0.99 * L, 2),
    value=round(0.50 * L, 2),
    step=round(L / 100, 2),
    format="%.2f",
)

R_A_tab = P * (L - a_tab) / L
R_B_tab = P * a_tab / L
M_max_tab = P * a_tab * (L - a_tab) / L

mc1, mc2, mc3 = st.columns(3)
mc1.metric("Reação  R_A", f"{R_A_tab:.1f} kN")
mc2.metric("Reação  R_B", f"{R_B_tab:.1f} kN")
mc3.metric("M máx  (em x = a)", f"{M_max_tab:.1f} kN·m")

# ── Formulário ───────────────────────────────────────────────────────────────
with st.expander("📐 Formulário — carga concentrada em posição variável"):
    st.latex(r"R_A = P\,\frac{L-a}{L} \qquad R_B = P\,\frac{a}{L}")
    st.latex(
        r"M(x) = \begin{cases} R_A\cdot x & 0 \le x \le a \\"
        r" R_B\cdot (L-x) & a \le x \le L \end{cases}"
    )
    st.latex(
        r"V(x) = \begin{cases} +R_A & 0 \le x < a \\ -R_B & a < x \le L \end{cases}"
    )
    st.latex(r"M_{\max} = \frac{P\,a\,(L-a)}{L} \quad \text{em } x = a")
    st.markdown(
        "O **envelope** (linha amarela tracejada) acumula o maior M possível em cada "
        "seção para qualquer posição da carga — base do dimensionamento de pontes e "
        "estruturas com cargas móveis."
    )
