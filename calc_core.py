"""
Núcleo de cálculo da Calculadora de Viga Biapoiada.

Funções puras (sem dependência de Streamlit) usadas tanto pela página de
cálculo individual (app.py) quanto pela página de cálculo em lote.
"""

import math

import numpy as np

# ---------------------------------------------------------------------------
# Parâmetros fixos (V2 — não pede ao usuário)
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
    d_cm = h_cm - COB_CM - PHI_EST_CM - PHI_LONG_CM / 2.0

    fcd_MPa = FCK_MPA / GAMMA_C
    fyd_MPa = FYK_MPA / GAMMA_S
    fcd_kNcm2 = fcd_MPa / 10.0
    fyd_kNcm2 = fyd_MPa / 10.0

    Md_kNm = M_max_kNm * GAMMA_F
    Md_kNcm = Md_kNm * 100.0

    As_min_cm2 = 0.0015 * b_cm * h_cm
    As_max_cm2 = 0.04 * b_cm * h_cm

    resultado = {
        "d_cm": d_cm,
        "fcd_MPa": fcd_MPa,
        "fyd_MPa": fyd_MPa,
        "Md_kNm": Md_kNm,
        "As_min_cm2": As_min_cm2,
        "As_max_cm2": As_max_cm2,
    }

    Kmd = Md_kNcm / (ALPHA_C * b_cm * d_cm**2 * fcd_kNcm2)
    resultado["Kmd"] = Kmd

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

    x_LN_cm = d_cm * (1.0 - np.sqrt(1.0 - 2.0 * Kmd)) / 0.8
    csi = x_LN_cm / d_cm
    resultado["x_LN_cm"] = x_LN_cm
    resultado["csi"] = csi

    if csi <= CSI_23:
        dominio = "Domínio 2"
        dom_status = "ok"
    elif csi <= CSI_34:
        dominio = "Domínio 3"
        dom_status = "ressalva" if csi > CSI_DUCTIL else "ok"
    else:
        dominio = "Domínio 4"
        dom_status = "alerta"
    resultado["dominio"] = dominio
    resultado["dom_status"] = dom_status

    As_calc_cm2 = Md_kNcm / (fyd_kNcm2 * (d_cm - 0.4 * x_LN_cm))
    resultado["As_calc_cm2"] = As_calc_cm2

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


def n_barras_armadura(As_adotado_cm2) -> int:
    """Estima nº de barras Ø12,5 mm — mín 2, máx 6."""
    if As_adotado_cm2 is None or (isinstance(As_adotado_cm2, float) and np.isnan(As_adotado_cm2)):
        return 0
    AREA_PHI125_CM2 = 1.25
    n = math.ceil(As_adotado_cm2 / AREA_PHI125_CM2)
    return max(2, min(6, n))
