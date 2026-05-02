import streamlit as st


def calcular_viga(L_m: float, q_kN_m: float) -> dict:
    RA_kN = (q_kN_m * L_m) / 2
    RB_kN = RA_kN
    Vmax_kN = RA_kN
    Mmax_kN_m = (q_kN_m * L_m**2) / 8
    return {
        "RA_kN": RA_kN,
        "RB_kN": RB_kN,
        "Vmax_kN": Vmax_kN,
        "Mmax_kN_m": Mmax_kN_m,
    }


def parse_float(texto: str) -> float:
    return float(texto.strip().replace(",", "."))


def main():
    st.title("Calculadora de Viga Biapoiada")
    st.write("Carga distribuída uniforme — Análise estática (Teoria de Euler-Bernoulli)")

    col1, col2 = st.columns(2)
    with col1:
        input_L = st.text_input("Comprimento L (m) — entre 0,5 e 30 m", placeholder="Ex: 6.0")
    with col2:
        input_q = st.text_input("Carga distribuída q (kN/m) — entre 0,1 e 200 kN/m", placeholder="Ex: 20.0")

    if st.button("Calcular"):
        erros = []

        try:
            L = parse_float(input_L)
        except (ValueError, AttributeError):
            erros.append("L inválido: informe um número (ex: 4.0 ou 4,0).")
            L = None

        try:
            q = parse_float(input_q)
        except (ValueError, AttributeError):
            erros.append("q inválido: informe um número (ex: 5.0 ou 5,0).")
            q = None

        if L is not None:
            if L <= 0:
                erros.append("L deve ser positivo.")
            elif L < 0.5 or L > 30:
                erros.append("L fora do domínio: deve estar entre 0,5 m e 30 m.")

        if q is not None:
            if q <= 0:
                erros.append("q deve ser positivo.")
            elif q < 0.1 or q > 200:
                erros.append("q fora do domínio: deve estar entre 0,1 kN/m e 200 kN/m.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            r = calcular_viga(L, q)

            st.success("Resultados")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("RA", f"{r['RA_kN']:.4f} kN")
            col_b.metric("RB", f"{r['RB_kN']:.4f} kN")
            col_c.metric("Vmax", f"{r['Vmax_kN']:.4f} kN")
            col_d.metric("Mmax", f"{r['Mmax_kN_m']:.4f} kN·m")

    st.caption(
        "⚠️ Ferramenta educacional e demonstrativa. Não substitui verificação normativa "
        "nem análise por engenheiro habilitado. Resultados não devem ser usados em projetos reais."
    )


if __name__ == "__main__":
    main()
