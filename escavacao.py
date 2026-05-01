"""
Cálculo de produtividade de escavação (m³/h) para escavadeiras hidráulicas.

Baseado em dados de fabricantes (Caterpillar, Komatsu, Volvo) e normas TCPO.
"""

# Capacidade da caçamba por classe de escavadeira (m³)
CACAMBA_M3 = {
    14: 0.50,
    20: 0.80,
    30: 1.20,
    40: 1.60,
    50: 2.00,
}

# Fator de enchimento da caçamba por tipo de material (0–1)
FATOR_ENCHIMENTO = {
    "solo":          1.00,  # solo comum, fácil de escavar
    "areia":         0.95,
    "argila":        0.90,
    "brita":         0.85,
    "rocha_mole":    0.75,  # rocha alterada / meia-rocha
    "rocha_dura":    0.60,  # rocha sã, necessita desmonte prévio
}

# Ciclo teórico por classe (segundos): giro 90°, carga + descarga típicos
CICLO_BASE_S = {
    14: 18,
    20: 20,
    30: 22,
    40: 24,
    50: 26,
}

# Fator de eficiência operacional (horas produtivas / hora paga)
EFICIENCIA = 0.75  # 45 min produtivos por hora


def _classe_mais_proxima(tonelagem: float) -> int:
    """Retorna a classe de escavadeira mais próxima da lista suportada."""
    classes = sorted(CACAMBA_M3.keys())
    return min(classes, key=lambda c: abs(c - tonelagem))


def escavacao(material: str = "solo", escavadeira: float = 20) -> float:
    """
    Calcula a produtividade de escavação em m³/h.

    Parâmetros
    ----------
    material : str
        Tipo de material a escavar. Opções:
        'solo', 'areia', 'argila', 'brita', 'rocha_mole', 'rocha_dura'
    escavadeira : float
        Classe da escavadeira em toneladas (peso operacional).
        Valores suportados: 14 t, 20 t, 30 t, 40 t, 50 t.
        Outros valores são aproximados para a classe mais próxima.

    Retorna
    -------
    float
        Produtividade em m³/h (banco, material in situ).

    Exemplo
    -------
    >>> escavacao()
    108.0
    >>> escavacao("rocha_mole", 30)
    110.45...
    """
    material = material.lower().strip()
    if material not in FATOR_ENCHIMENTO:
        opcoes = ", ".join(FATOR_ENCHIMENTO)
        raise ValueError(f"Material '{material}' desconhecido. Use: {opcoes}")

    classe = _classe_mais_proxima(escavadeira)
    cacamba   = CACAMBA_M3[classe]           # m³
    f_enc     = FATOR_ENCHIMENTO[material]   # adimensional
    ciclo_s   = CICLO_BASE_S[classe]         # segundos

    ciclos_por_hora = 3600 / ciclo_s
    produtividade   = cacamba * f_enc * ciclos_por_hora * EFICIENCIA

    return round(produtividade, 2)


if __name__ == "__main__":
    print(f"{'Material':<12} {'Escavadeira':>12} {'Produtividade':>16}")
    print("-" * 42)
    casos = [
        ("solo",       20),
        ("areia",      20),
        ("argila",     20),
        ("brita",      30),
        ("rocha_mole", 30),
        ("rocha_dura", 40),
    ]
    for mat, ton in casos:
        prod = escavacao(mat, ton)
        print(f"{mat:<12} {ton:>9} t   {prod:>12.1f} m³/h")
