"""
Página de cálculo em lote — recebe Excel com várias vigas, calcula todas
de uma vez e devolve a planilha enriquecida com os resultados.

Reusa as funções puras de calc_core.py (mesmas usadas pelo app individual).
"""

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from calc_core import (
    DISCLAIMER,
    calcular_esforcos,
    dimensionar_armadura,
)

# ---------------------------------------------------------------------------
# Constantes da página
# ---------------------------------------------------------------------------
COLUNAS_OBRIGATORIAS = ["viga_id", "L", "q", "b", "h", "descricao"]
LIMITES = {
    "L": (1.0, 20.0),     # m
    "q": (0.5, 100.0),    # kN/m
    "b": (12, 40),        # cm
    "h": (30, 100),       # cm
}
LIMITE_LINHAS = 1000
LIMITE_ARQUIVO_MB = 5

EXEMPLO_PATH = Path(__file__).resolve().parent.parent / "exemplos" / "vigas_exemplo.xlsx"


# ---------------------------------------------------------------------------
# Helpers — Excel
# ---------------------------------------------------------------------------
def _df_para_xlsx_bytes(df: pd.DataFrame, nome_aba: str = "vigas") -> bytes:
    """Serializa um DataFrame em bytes .xlsx (engine openpyxl)."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=nome_aba, index=False)
    return buf.getvalue()


def gerar_template_vazio() -> bytes:
    """Excel só com o cabeçalho — para o usuário preencher."""
    df = pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
    return _df_para_xlsx_bytes(df, "template")


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
def validar_schema(df: pd.DataFrame) -> list[str]:
    """Retorna lista de erros de schema. Vazia = OK."""
    erros = []
    faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltantes:
        erros.append(f"Colunas obrigatórias faltando: {', '.join(faltantes)}")
    if df.empty:
        erros.append("Planilha vazia (nenhuma linha de dados).")
    if len(df) > LIMITE_LINHAS:
        erros.append(
            f"Limite de {LIMITE_LINHAS} vigas por planilha. "
            f"Sua planilha tem {len(df)} linhas."
        )
    return erros


def validar_linha(row: pd.Series) -> tuple[bool, str]:
    """
    Valida uma linha individual. Retorna (ok, mensagem).
    Linha inválida não é processada — apenas marcada com erro.
    """
    # viga_id obrigatório
    if pd.isna(row.get("viga_id")) or str(row.get("viga_id")).strip() == "":
        return False, "viga_id vazio"

    # numéricos obrigatórios
    for col in ("L", "q", "b", "h"):
        valor = row.get(col)
        if pd.isna(valor):
            return False, f"{col} vazio"
        try:
            float(valor)
        except (TypeError, ValueError):
            return False, f"{col} não-numérico ({valor!r})"

    # limites de domínio
    for col, (lo, hi) in LIMITES.items():
        v = float(row[col])
        if v < lo or v > hi:
            return False, f"{col}={v:g} fora do intervalo [{lo:g}, {hi:g}]"

    return True, ""


# ---------------------------------------------------------------------------
# Processamento em lote
# ---------------------------------------------------------------------------
def processar_lote(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada linha válida, chama calcular_esforcos + dimensionar_armadura.
    Mantém colunas originais e acrescenta colunas calculadas à direita.
    """
    out = df.copy()

    # Pré-aloca colunas de saída
    novas_colunas = {
        "M_max_kNm": [],
        "V_max_kN": [],
        "As_adotado_cm2": [],
        "dominio": [],
        "status": [],
        "mensagem": [],
    }

    for _, row in out.iterrows():
        ok, msg_erro = validar_linha(row)
        if not ok:
            novas_colunas["M_max_kNm"].append(float("nan"))
            novas_colunas["V_max_kN"].append(float("nan"))
            novas_colunas["As_adotado_cm2"].append(float("nan"))
            novas_colunas["dominio"].append("—")
            novas_colunas["status"].append("erro_input")
            novas_colunas["mensagem"].append(msg_erro)
            continue

        L = float(row["L"])
        q = float(row["q"])
        b = float(row["b"])
        h = float(row["h"])

        M_max, V_max = calcular_esforcos(L, q)
        r = dimensionar_armadura(b, h, M_max)

        novas_colunas["M_max_kNm"].append(round(M_max, 3))
        novas_colunas["V_max_kN"].append(round(V_max, 3))
        novas_colunas["As_adotado_cm2"].append(
            round(r["As_adotado_cm2"], 3)
            if not pd.isna(r["As_adotado_cm2"]) else float("nan")
        )
        novas_colunas["dominio"].append(r["dominio"])
        novas_colunas["status"].append(r["status"])
        novas_colunas["mensagem"].append(r["mensagem"])

    for col, valores in novas_colunas.items():
        out[col] = valores

    return out


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Cálculo em Lote — Vigas",
        page_icon="📋",
        layout="wide",
    )
    st.title("📋 Cálculo em Lote de Vigas")
    st.warning(f"⚠️ {DISCLAIMER}")

    st.markdown(
        "Faça upload de uma planilha **.xlsx** com várias vigas e baixe os "
        "resultados calculados (M_max, V_max, As, domínio) em uma única operação."
    )

    # ---- 1. Template e exemplo --------------------------------------------
    st.subheader("1. Baixar modelo")
    col_t, col_e = st.columns(2)
    with col_t:
        st.download_button(
            label="📥 Template vazio (.xlsx)",
            data=gerar_template_vazio(),
            file_name="template_vigas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Cabeçalho com as colunas obrigatórias.",
        )
    with col_e:
        if EXEMPLO_PATH.exists():
            with open(EXEMPLO_PATH, "rb") as f:
                st.download_button(
                    label="📥 Exemplo com 10 vigas (.xlsx)",
                    data=f.read(),
                    file_name="vigas_exemplo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Planilha de demonstração já preenchida.",
                )
        else:
            st.caption("(arquivo de exemplo não encontrado)")

    with st.expander("ℹ️ Schema esperado"):
        st.markdown(
            f"""
| Coluna       | Tipo  | Limite                              |
|--------------|-------|-------------------------------------|
| `viga_id`    | texto | obrigatório                         |
| `L`          | float | {LIMITES['L'][0]:g} a {LIMITES['L'][1]:g} m       |
| `q`          | float | {LIMITES['q'][0]:g} a {LIMITES['q'][1]:g} kN/m    |
| `b`          | int   | {LIMITES['b'][0]} a {LIMITES['b'][1]} cm           |
| `h`          | int   | {LIMITES['h'][0]} a {LIMITES['h'][1]} cm          |
| `descricao`  | texto | opcional                            |

**Limites:** máx. {LIMITE_LINHAS} vigas por planilha · arquivo até {LIMITE_ARQUIVO_MB} MB.
            """
        )

    st.divider()

    # ---- 2. Upload --------------------------------------------------------
    st.subheader("2. Upload da planilha")
    arquivo = st.file_uploader(
        "Selecione o .xlsx",
        type=["xlsx"],
        help=f"Máx. {LIMITE_ARQUIVO_MB} MB.",
    )
    if arquivo is None:
        st.info("Aguardando upload do arquivo .xlsx.")
        return

    if arquivo.size > LIMITE_ARQUIVO_MB * 1024 * 1024:
        st.error(
            f"Arquivo muito grande ({arquivo.size / 1e6:.1f} MB). "
            f"Limite: {LIMITE_ARQUIVO_MB} MB."
        )
        return

    try:
        df = pd.read_excel(arquivo, engine="openpyxl")
    except Exception as exc:
        st.error(f"Não foi possível ler o arquivo .xlsx: {exc}")
        return

    erros_schema = validar_schema(df)
    if erros_schema:
        for e in erros_schema:
            st.error(e)
        return

    df = df[COLUNAS_OBRIGATORIAS].copy()

    st.success(f"Arquivo lido com sucesso — {len(df)} linha(s).")
    with st.expander("👁️ Pré-visualização (até 50 linhas)"):
        st.dataframe(df.head(50), use_container_width=True)

    # ---- 3. Processamento -------------------------------------------------
    st.subheader("3. Processar")
    if not st.button("▶️ Calcular lote", type="primary"):
        return

    with st.spinner("Calculando..."):
        resultado = processar_lote(df)

    # Resumo
    contagem = resultado["status"].value_counts().to_dict()
    n_total = len(resultado)
    n_ok = contagem.get("ok", 0)
    n_min = contagem.get("min", 0)
    n_erro_calc = contagem.get("erro", 0)
    n_erro_input = contagem.get("erro_input", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", n_total)
    c2.metric("✅ OK", n_ok)
    c3.metric("ℹ️ As_min", n_min)
    c4.metric("⚠️ Inviável", n_erro_calc)
    c5.metric("❌ Input ruim", n_erro_input)

    st.subheader("Resultado")
    st.dataframe(resultado, use_container_width=True)

    # ---- 4. Download ------------------------------------------------------
    xlsx_bytes = _df_para_xlsx_bytes(resultado, "resultado")
    st.download_button(
        label="📥 Baixar planilha calculada (.xlsx)",
        data=xlsx_bytes,
        file_name="vigas_calculadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


if __name__ == "__main__":
    main()
