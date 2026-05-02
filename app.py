"""
Calculadora de Viga Biapoiada — V3
Cálculo de esforços + dimensionamento de armadura passiva por flexão simples
conforme NBR 6118 (concreto C30, aço CA-50, CAA II).
V3: visualização 3D rotacionável com cor mapeada por |M(x)| e armadura.
"""

import math

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
def n_barras_armadura(As_adotado_cm2) -> int:
    """Estima nº de barras Ø12,5 mm — mín 2, máx 6."""
    if As_adotado_cm2 is None or (isinstance(As_adotado_cm2, float) and np.isnan(As_adotado_cm2)):
        return 0
    AREA_PHI125_CM2 = 1.25  # área aproximada da Ø12,5 (especificação V3)
    n = math.ceil(As_adotado_cm2 / AREA_PHI125_CM2)
    return max(2, min(6, n))


def montar_memoria(L, q, b, h, descricao, M_max, V_max, r, n_barras: int) -> str:
    nome = descricao.strip() if descricao and descricao.strip() else "(sem identificação)"

    def fmt(v, casas=2):
        return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{casas}f}"

    barras_txt = f"{n_barras} × Ø12,5 mm" if n_barras > 0 else "— (seção inviável)"

    return f"""# Memória de Cálculo — Viga {nome}

## Dados de entrada
- Vão (L): {L:.2f} m
- Carga distribuída (q): {q:.2f} kN/m
- Seção: b = {b:.1f} cm × h = {h:.1f} cm

## Parâmetros adotados
- Concreto: C25 (fck = 25 MPa)
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

## Visualização 3D
- Discretização do vão: 20 segmentos
- Mapeamento de cor: |M(x)| → RdYlGn_r (verde nos apoios → vermelho no meio do vão)
- Armadura representada: {barras_txt}
- Cobertura: 30 mm (CAA II)

## Pedido para auditoria
Por favor, audite os cálculos acima conforme NBR 6118. Verifique:
1. Fórmulas de dimensionamento estão corretas?
2. Verificação de domínio está adequada?
3. Limite de armadura mínima foi respeitado?
4. Algum aspecto de segurança que faltou considerar?
"""


# ---------------------------------------------------------------------------
# Visualização 3D (V3) — geometria via Plotly graph_objects
# ---------------------------------------------------------------------------
N_SEGMENTOS_3D = 20            # discretização do vão (especificação V3)
N_SETAS_CARGA = 9              # nº de setas representando q
COR_BARRAS = "#FFA500"         # laranja-amarelo
COR_SETAS = "#D62728"          # vermelho


def _construir_viga_mesh(L_m: float, b_cm: float, h_cm: float, q: float):
    """
    Constrói o paralelepípedo da viga como Mesh3d com cor por |M(x)|.
    21 seções transversais × 4 vértices = 84 vértices; ~164 triângulos.
    """
    b_m = b_cm / 100.0
    h_m = h_cm / 100.0
    n_sec = N_SEGMENTOS_3D + 1

    x_secs = np.linspace(0.0, L_m, n_sec)
    M_secs = q * x_secs * (L_m - x_secs) / 2.0  # M(x) ≥ 0 em viga biapoiada

    # 4 vértices por seção: (0,0), (b,0), (b,h), (0,h) em y/z
    cantos_yz = [(0.0, 0.0), (b_m, 0.0), (b_m, h_m), (0.0, h_m)]

    vx, vy, vz, intensidade = [], [], [], []
    for x_i, M_i in zip(x_secs, M_secs):
        for (y_i, z_i) in cantos_yz:
            vx.append(float(x_i))
            vy.append(y_i)
            vz.append(z_i)
            intensidade.append(abs(float(M_i)))

    i_idx, j_idx, k_idx = [], [], []

    def add_quad(a, b, c, d):
        """Adiciona dois triângulos (a,b,c) e (a,c,d) para um quadrilátero."""
        i_idx.extend([a, a])
        j_idx.extend([b, c])
        k_idx.extend([c, d])

    # Tampas das extremidades
    add_quad(0, 1, 2, 3)                       # x = 0
    base_fim = 4 * N_SEGMENTOS_3D
    add_quad(base_fim + 0, base_fim + 3, base_fim + 2, base_fim + 1)  # x = L

    # Faces laterais entre seções consecutivas
    for s in range(N_SEGMENTOS_3D):
        a0 = 4 * s          # vértices da seção s: a0+0..a0+3
        a1 = 4 * (s + 1)    # vértices da seção s+1
        # face inferior (z=0)
        add_quad(a0 + 0, a1 + 0, a1 + 1, a0 + 1)
        # face superior (z=h)
        add_quad(a0 + 3, a0 + 2, a1 + 2, a1 + 3)
        # face fundo (y=0)
        add_quad(a0 + 0, a0 + 3, a1 + 3, a1 + 0)
        # face frente (y=b)
        add_quad(a0 + 1, a1 + 1, a1 + 2, a0 + 2)

    return dict(
        x=vx, y=vy, z=vz,
        i=i_idx, j=j_idx, k=k_idx,
        intensity=intensidade,
    )


def _construir_barras(L_m: float, b_cm: float, h_cm: float, n_barras: int):
    """
    Linhas das barras longitudinais paralelas ao eixo x.
    z = cob + φ_estribo + φ_long/2  (consistente com d do dimensionamento).
    """
    if n_barras <= 0:
        return [], [], []

    b_m = b_cm / 100.0
    cob_m = COB_CM / 100.0
    phi_est_m = PHI_EST_CM / 100.0
    phi_long_m = PHI_LONG_CM / 100.0

    z_barra = cob_m + phi_est_m + phi_long_m / 2.0
    offset_lateral = cob_m + phi_est_m

    if n_barras == 1:
        ys = [b_m / 2.0]
    else:
        y_min = offset_lateral
        y_max = b_m - offset_lateral
        ys = np.linspace(y_min, y_max, n_barras).tolist()

    xs, ys_full, zs = [], [], []
    for y_i in ys:
        # separador None entre barras → traço descontínuo numa única trace
        xs.extend([0.0, L_m, None])
        ys_full.extend([y_i, y_i, None])
        zs.extend([z_barra, z_barra, None])
    return xs, ys_full, zs


def _construir_setas_carga(L_m: float, h_m: float, b_m: float, q: float):
    """Hastes (Scatter3d) e cabeças (Cone) das setas representando q."""
    # Comprimento da haste cresce com q, mas saturado para não estourar a vista
    shaft_len = float(np.clip(0.20 + q * 0.005, 0.20, 0.60))
    cone_size = 0.06  # altura do cone em metros

    x_setas = np.linspace(L_m * 0.05, L_m * 0.95, N_SETAS_CARGA)

    # Hastes verticais (do topo da seta até logo acima da cabeça)
    xs, ys, zs = [], [], []
    for x_i in x_setas:
        xs.extend([float(x_i), float(x_i), None])
        ys.extend([b_m / 2.0, b_m / 2.0, None])
        zs.extend([h_m + shaft_len, h_m + cone_size, None])

    # Cones com tip tocando o topo da viga, apontando pra baixo
    cone_x = [float(x) for x in x_setas]
    cone_y = [b_m / 2.0] * N_SETAS_CARGA
    cone_z = [h_m] * N_SETAS_CARGA
    cone_u = [0.0] * N_SETAS_CARGA
    cone_v = [0.0] * N_SETAS_CARGA
    cone_w = [-1.0] * N_SETAS_CARGA

    return (xs, ys, zs), (cone_x, cone_y, cone_z, cone_u, cone_v, cone_w), cone_size


def _construir_apoios(L_m: float, b_cm: float):
    """
    Dois prismas triangulares cinzas embaixo das extremidades.
    6 vértices/apoio, 8 triângulos/apoio (16 no total).
    """
    b_m = b_cm / 100.0
    altura = 0.15
    meia_base = 0.10

    vx, vy, vz = [], [], []
    i_idx, j_idx, k_idx = [], [], []

    for x_a in (0.0, L_m):
        base = len(vx)
        # Aresta superior (toca a viga em z=0): v0 (y=0), v1 (y=b)
        vx.extend([x_a, x_a])
        vy.extend([0.0, b_m])
        vz.extend([0.0, 0.0])
        # Aresta inferior esquerda: v2 (y=0), v3 (y=b)
        vx.extend([x_a - meia_base, x_a - meia_base])
        vy.extend([0.0, b_m])
        vz.extend([-altura, -altura])
        # Aresta inferior direita: v4 (y=0), v5 (y=b)
        vx.extend([x_a + meia_base, x_a + meia_base])
        vy.extend([0.0, b_m])
        vz.extend([-altura, -altura])

        v0, v1, v2, v3, v4, v5 = base, base + 1, base + 2, base + 3, base + 4, base + 5
        # face esquerda (sloping)
        i_idx.extend([v0, v0]); j_idx.extend([v2, v3]); k_idx.extend([v3, v1])
        # face direita
        i_idx.extend([v0, v0]); j_idx.extend([v1, v5]); k_idx.extend([v5, v4])
        # face inferior
        i_idx.extend([v2, v2]); j_idx.extend([v4, v5]); k_idx.extend([v5, v3])
        # tampa y=0
        i_idx.extend([v0]); j_idx.extend([v2]); k_idx.extend([v4])
        # tampa y=b
        i_idx.extend([v1]); j_idx.extend([v5]); k_idx.extend([v3])

    return dict(x=vx, y=vy, z=vz, i=i_idx, j=j_idx, k=k_idx)


def render_3d(L, q, b, h, descricao, M_max, r):
    nome = descricao.strip() if descricao and descricao.strip() else "(sem identificação)"
    n_barras = n_barras_armadura(r.get("As_adotado_cm2"))
    b_m = b / 100.0
    h_m = h / 100.0

    fig = go.Figure()

    # 1. Paralelepípedo da viga colorido por |M(x)|
    mesh_viga = _construir_viga_mesh(L, b, h, q)
    fig.add_trace(go.Mesh3d(
        **mesh_viga,
        colorscale="RdYlGn_r",
        cmin=0.0,
        cmax=float(M_max) if M_max > 0 else 1.0,
        showscale=True,
        colorbar=dict(
            title=dict(text="|M(x)|<br>(kN·m)", side="right"),
            x=1.02, len=0.7, thickness=14,
        ),
        flatshading=False,
        opacity=1.0,
        lighting=dict(ambient=0.65, diffuse=0.75, specular=0.1),
        hovertemplate=("x = %{x:.2f} m<br>|M| = %{intensity:.2f} kN·m"
                       "<extra></extra>"),
        name="Viga",
    ))

    # 2. Apoios estilizados
    apoios = _construir_apoios(L, b)
    fig.add_trace(go.Mesh3d(
        **apoios,
        color="#888888",
        opacity=0.85,
        flatshading=True,
        showscale=False,
        hoverinfo="skip",
        name="Apoios",
    ))

    # 3. Hastes das setas de carga
    (sx, sy, sz), (cx, cy, cz, cu, cv, cw), cone_size = _construir_setas_carga(L, h_m, b_m, q)
    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode="lines",
        line=dict(color=COR_SETAS, width=5),
        name=f"Carga q = {q:.1f} kN/m",
        hoverinfo="skip",
        showlegend=True,
    ))
    # 4. Cabeças das setas de carga
    fig.add_trace(go.Cone(
        x=cx, y=cy, z=cz, u=cu, v=cv, w=cw,
        anchor="tip",
        sizemode="absolute",
        sizeref=cone_size,
        colorscale=[[0, COR_SETAS], [1, COR_SETAS]],
        showscale=False,
        showlegend=False,
        hoverinfo="skip",
    ))

    # 5. Armadura longitudinal
    if n_barras > 0:
        bx, by, bz = _construir_barras(L, b, h, n_barras)
        fig.add_trace(go.Scatter3d(
            x=bx, y=by, z=bz,
            mode="lines",
            line=dict(color=COR_BARRAS, width=8),
            name=f"{n_barras} × Ø12,5 mm",
            hovertemplate="Armadura longitudinal<extra></extra>",
        ))

    # Layout — câmera isométrica suave, eixos em metros, proporção real
    titulo = (f"Viga {nome} — L={L:g} m | b={b:g} cm × h={h:g} cm | "
              f"M_max={M_max:.2f} kN·m")
    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center", font=dict(size=14)),
        scene=dict(
            xaxis=dict(title="x (m) — vão", showgrid=True, backgroundcolor="white"),
            yaxis=dict(title="y (m) — largura", showgrid=True, backgroundcolor="white"),
            zaxis=dict(title="z (m) — altura", showgrid=True, backgroundcolor="white"),
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.0),
                projection=dict(type="perspective"),
            ),
        ),
        height=600,
        margin=dict(l=10, r=10, t=70, b=10),
        paper_bgcolor="white",
        legend=dict(x=0.0, y=1.0, bgcolor="rgba(255,255,255,0.7)"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Caixa explicativa
    info_armadura = (
        f"🟡 Linhas amarelas representam a armadura longitudinal calculada "
        f"({n_barras} barras Ø12,5 mm)"
        if n_barras > 0 else
        "🟡 Sem armadura representada (seção inviável — ver aba Resultados)"
    )
    st.info(
        "🎨 Cor representa intensidade do momento fletor M(x) — "
        "verde nos apoios, vermelho no meio do vão  \n"
        f"{info_armadura} — posicionadas no eixo do `d` "
        "(cobertura + estribo + φ/2)  \n"
        f"🔻 Setas vermelhas representam a carga distribuída q  \n"
        "↻ Arraste para rotacionar · 🔍 Scroll para zoom · "
        "duplo-clique reseta a câmera"
    )


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
    n_barras = n_barras_armadura(r.get("As_adotado_cm2"))
    texto = montar_memoria(L, q, b, h, descricao, M_max, V_max, r, n_barras)
    st.markdown(texto)
    st.divider()
    st.markdown(
        "**Markdown bruto** (use o botão de copiar do bloco abaixo "
        "para colar em outra IA e pedir auditoria):"
    )
    st.code(texto, language="markdown")


def main():
    st.set_page_config(page_title="Viga Biapoiada V3", page_icon="🏗️", layout="wide")
    st.title("🏗️ Calculadora de Viga Biapoiada — V3")
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

    # 5 abas (V3 adiciona Visualização 3D)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Resultados", "📋 Tabela Pandas", "📈 Diagramas",
         "📄 Memória", "🏗️ Visualização 3D"]
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
    with tab5:
        render_3d(float(L), float(q), float(b), float(h),
                  descricao, M_max, r)

    st.divider()
    st.caption(f"⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()
