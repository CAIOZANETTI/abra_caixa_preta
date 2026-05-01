import streamlit as st
import pandas as pd
from escavacao import (
    escavacao,
    FATOR_ENCHIMENTO,
    CACAMBA_M3,
    CICLO_BASE_S,
    EFICIENCIA,
    _classe_mais_proxima,
)

LABEL_MATERIAL = {
    "solo":       "Solo comum",
    "areia":      "Areia",
    "argila":     "Argila",
    "brita":      "Brita / Cascalho",
    "rocha_mole": "Rocha mole (alterada)",
    "rocha_dura": "Rocha dura (sã)",
}

st.set_page_config(page_title="Produtividade de Escavação", page_icon="🏗️", layout="centered")

st.title("🏗️ Produtividade de Escavação")
st.caption("Cálculo baseado em dados TCPO e fabricantes (Cat, Komatsu, Volvo)")

st.divider()

col1, col2 = st.columns(2)

with col1:
    material_label = st.selectbox(
        "Tipo de material",
        options=list(LABEL_MATERIAL.values()),
        index=0,
    )
    material_key = next(k for k, v in LABEL_MATERIAL.items() if v == material_label)

with col2:
    classes = sorted(CACAMBA_M3.keys())
    escavadeira_t = st.select_slider(
        "Classe da escavadeira (t)",
        options=classes,
        value=20,
    )

eficiencia_pct = st.slider(
    "Eficiência operacional (%)",
    min_value=30,
    max_value=95,
    value=int(EFICIENCIA * 100),
    step=5,
    help="Percentual de horas produtivas por hora paga. Padrão TCPO: 75%.",
)

st.divider()

classe     = _classe_mais_proxima(escavadeira_t)
cacamba    = CACAMBA_M3[classe]
f_enc      = FATOR_ENCHIMENTO[material_key]
ciclo_s    = CICLO_BASE_S[classe]
efic       = eficiencia_pct / 100

ciclos_h   = 3600 / ciclo_s
prod       = round(cacamba * f_enc * ciclos_h * efic, 2)

prod_turno = round(prod * 8, 1)
prod_dia   = round(prod * 10, 1)

st.subheader("Resultado")

m1, m2, m3 = st.columns(3)
m1.metric("Produtividade", f"{prod:.1f} m³/h")
m2.metric("Por turno (8 h)", f"{prod_turno:.0f} m³")
m3.metric("Por jornada (10 h)", f"{prod_dia:.0f} m³")

with st.expander("Detalhes do cálculo"):
    st.markdown(f"""
| Parâmetro | Valor |
|---|---|
| Material | {material_label} |
| Fator de enchimento | {f_enc:.0%} |
| Caçamba (classe {classe} t) | {cacamba} m³ |
| Ciclo base | {ciclo_s} s |
| Ciclos por hora | {ciclos_h:.0f} |
| Eficiência operacional | {eficiencia_pct}% |

**Fórmula:**
`produtividade = caçamba × fator_enchimento × ciclos/h × eficiência`
`{prod:.2f} = {cacamba} × {f_enc} × {ciclos_h:.0f} × {efic}`
""")

st.divider()
st.subheader("Comparativo — todos os materiais")

rows = []
for key, label in LABEL_MATERIAL.items():
    p = round(CACAMBA_M3[classe] * FATOR_ENCHIMENTO[key] * ciclos_h * efic, 1)
    rows.append({"Material": label, "m³/h": p, "m³/turno (8h)": round(p * 8, 0)})

df = pd.DataFrame(rows).set_index("Material")
st.dataframe(df, use_container_width=True)
st.bar_chart(df["m³/h"])
