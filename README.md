# Calculadora de Momento e Cortante para Viga Biapoiada

Ferramenta web simples em Python para calcular o momento fletor máximo e o esforço cortante máximo em uma viga biapoiada submetida a carga distribuída uniforme.

> ⚠️ **Aviso ao leitor (humano ou IA):** este README é o **contrato técnico** do projeto. Qualquer geração de código deve respeitar literalmente as fórmulas, hipóteses, limites, casos de teste e proibições aqui descritos. Quando houver dúvida, **parar e perguntar** — não inferir, não generalizar, não inventar feature.

---

## 1. Propósito do projeto

Calculadora educacional para análise estática elementar de viga biapoiada com carga distribuída uniforme. Não é ferramenta de projeto estrutural.

---

## 2. Hipóteses do modelo

O modelo desta V1 assume **rigorosamente** o seguinte:

* Viga **biapoiada** (apoio simples nas duas extremidades, sem balanços).
* Viga **prismática** (seção constante ao longo do vão).
* Material **homogêneo, isotrópico, elástico-linear**.
* **Pequenas deformações** (teoria de vigas de Euler-Bernoulli em regime linear).
* **Sem efeitos de 2ª ordem**, sem flambagem lateral, sem torção.
* **Apoios pontuais ideais** (sem largura, sem rigidez à rotação, sem recalque).
* **Carga distribuída uniforme** ao longo de todo o vão (sem cargas pontuais, sem cargas variáveis, sem momentos aplicados).
* Análise puramente estática (sem efeitos dinâmicos, vibração ou impacto).

Qualquer situação real que não atenda a **todas** essas hipóteses está fora do escopo da ferramenta.

---

## 3. Convenção de sinais

Adotada de forma explícita para evitar ambiguidade na implementação e na visualização:

* **Esforço cortante V positivo:** soma das forças verticais à esquerda do corte apontadas para cima (convenção clássica da estática estrutural).
* **Momento fletor M positivo:** quando traciona a fibra inferior da viga (convexidade para baixo).
* **Eixo x:** origem no apoio A (esquerdo), positivo para a direita até o apoio B em `x = L`.

---

## 4. Fórmulas e unidades

### 4.1 Entrada de dados

| Variável | Descrição                  | Unidade | Símbolo de display |
| -------- | -------------------------- | ------- | ------------------ |
| `L`      | Vão da viga                | m       | m                  |
| `q`      | Carga distribuída uniforme | kN/m    | kN/m               |

> 🔎 **Sobre o peso próprio:** `q` representa a **carga total distribuída**, já incluindo peso próprio se aplicável. **O app não calcula peso próprio automaticamente** — é responsabilidade do usuário somar peso próprio e sobrecarga antes de inserir.

### 4.2 Reações nos apoios

Por simetria geométrica e de carregamento:

```text
RA = RB = (q × L) / 2
```

| Variável | Descrição                            | Unidade |
| -------- | ------------------------------------ | ------- |
| `RA`     | Reação no apoio A (esquerdo)         | kN      |
| `RB`     | Reação no apoio B (direito) — = RA   | kN      |

### 4.3 Esforço cortante máximo

Ocorre nos apoios, em módulo:

```text
Vmax = (q × L) / 2
```

| Variável | Descrição                        | Unidade |
| -------- | -------------------------------- | ------- |
| `Vmax`   | Esforço cortante máximo (módulo) | kN      |

### 4.4 Momento fletor máximo

Ocorre no meio do vão (`x = L/2`):

```text
Mmax = (q × L²) / 8
```

| Variável | Descrição             | Unidade |
| -------- | --------------------- | ------- |
| `Mmax`   | Momento fletor máximo | kN·m    |

### 4.5 Padronização de unidades

* **Display (interface):** usar sempre `m`, `kN`, `kN/m` e `kN·m` (com ponto centralizado U+00B7).
* **Variáveis Python:** usar `L_m`, `q_kN_m`, `RA_kN`, `RB_kN`, `Vmax_kN`, `Mmax_kN_m`.
* Não misturar formatos (`kN.m`, `kNm`, `kN m` ficam **proibidos**).

---

## 5. Domínio de validade dos inputs

A ferramenta só aceita valores dentro das faixas abaixo. Fora delas, o app deve **rejeitar a entrada com mensagem clara**, sem retornar resultado.

| Variável | Mínimo | Máximo  | Justificativa                                         |
| -------- | ------ | ------- | ----------------------------------------------------- |
| `L`      | 0,5 m  | 30 m    | Faixa típica de vigas biapoiadas em edificações.      |
| `q`      | 0,1 kN/m | 200 kN/m | Faixa típica para vigas de concreto/aço/madeira em uso. |

Regras adicionais de input:

* Aceitar **vírgula e ponto** como separador decimal (ex.: `3,5` e `3.5` → ambos válidos).
* Rejeitar entradas **não numéricas**, **vazias** ou **negativas** com mensagem explícita.
* Rejeitar valores **fora do domínio** com mensagem indicando o limite violado.

---

## 6. O que o usuário informa

1. Vão da viga `L`, em metros.
2. Carga distribuída uniforme `q`, em kN/m (já incluindo peso próprio se aplicável).

---

## 7. O que o app responde

| Resultado                    | Símbolo  | Unidade |
| ---------------------------- | -------- | ------- |
| Reação nos apoios (RA = RB)  | `RA=RB`  | kN      |
| Esforço cortante máximo      | `Vmax`   | kN      |
| Momento fletor máximo        | `Mmax`   | kN·m    |

> Nota: nesta V1, RA e RB são apresentados como um **único resultado** (`RA = RB`), porque a simetria é premissa do modelo. A ideia de "reações diferentes" é tratada apenas em V2+.

Esta V1 **não gera diagramas** de cortante ou momento.

---

## 8. Casos de teste de referência

Estes três casos são o **gabarito de validação**. Qualquer alteração de código (humana ou via IA) deve manter exatamente estes resultados.

### Caso 1 — Viga curta, carga leve

* Entrada: `L = 4,0 m`, `q = 5,0 kN/m`
* Esperado:
  * `RA = RB = 10,0 kN`
  * `Vmax = 10,0 kN`
  * `Mmax = 10,0 kN·m`

### Caso 2 — Viga média, carga típica

* Entrada: `L = 6,0 m`, `q = 20,0 kN/m`
* Esperado:
  * `RA = RB = 60,0 kN`
  * `Vmax = 60,0 kN`
  * `Mmax = 90,0 kN·m`

### Caso 3 — Viga longa, carga elevada

* Entrada: `L = 10,0 m`, `q = 50,0 kN/m`
* Esperado:
  * `RA = RB = 250,0 kN`
  * `Vmax = 250,0 kN`
  * `Mmax = 625,0 kN·m`

Tolerância numérica para os testes: **1×10⁻⁶** (resultados fechados, sem ponto flutuante crítico).

---

## 9. Bibliotecas usadas

```text
Python >= 3.10
streamlit == 1.39.0
```

### Dependências (`requirements.txt`)

```text
streamlit==1.39.0
```

Versões fixadas (pinadas) para evitar quebra silenciosa em atualizações do Streamlit Cloud.

---

## 10. Escopo da V1

### 10.1 Incluído

* Cálculo de viga biapoiada com carga distribuída uniforme.
* Reação nos apoios (única, por simetria).
* Esforço cortante máximo.
* Momento fletor máximo.
* Validação de inputs conforme item 5.
* Interface Streamlit minimalista.
* Suíte de testes com os 3 casos do item 8.
* Execução local e no Streamlit Cloud.
* Sem banco de dados.

### 10.2 Fora do escopo (V2+)

* Diagrama de esforço cortante.
* Diagrama de momento fletor.
* Cargas pontuais, triangulares, trapezoidais ou variáveis.
* Vigas contínuas, em balanço, biengastadas ou hiperestáticas.
* Combinações de carga (ELU, ELS, ações permanentes/variáveis).
* Cálculo de armadura.
* Dimensionamento de seção.
* Verificação normativa.
* Verificação de flecha.
* Login, banco de dados, salvamento de projetos.

### 10.3 🚫 Proibições explícitas para a IA

Mesmo que o usuário peça, **a V1 não pode**:

* Calcular ou sugerir **armadura** (longitudinal, transversal, ancoragem).
* Sugerir **seção de viga** (h, b, perfis metálicos, classe de concreto, classe de madeira).
* Realizar verificação de **ELU** ou **ELS** (flecha, fissuração, vibração).
* Citar **NBR específica** (NBR 6118, NBR 8681, NBR 8800, NBR 7190 etc.) **como se estivesse implementada** — pode-se mencionar apenas no disclaimer que **não há** verificação normativa.
* Adicionar campos de **peso próprio automático**, **fator de segurança** ou **coeficientes de ponderação**.
* Adicionar **cargas pontuais** ou **trechos de carga** mesmo que pareça "simples".
* Gerar **gráficos** de cortante/momento (reservado para V2).
* Inferir resultados a partir de fotos, plantas ou descrições textuais (parsing NLP de escopo está fora).

Se o usuário solicitar qualquer item desta lista, o comportamento esperado é **não implementar** e indicar que está fora do escopo da V1.

---

## 11. Estrutura mínima do projeto

```text
.
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
└── tests/
    └── test_viga.py
```

`tests/test_viga.py` deve cobrir os três casos de teste do item 8.

---

## 12. Como executar localmente

```bash
git clone <url-do-repositorio>
cd <nome-do-repositorio>
pip install -r requirements.txt
streamlit run app.py
```

Para rodar os testes:

```bash
python -m pytest tests/
```

---

## 13. Deploy no Streamlit Cloud

App pensado para rodar no Streamlit Cloud com a estrutura mínima do item 11. O Streamlit Cloud executa `app.py` diretamente, sem necessidade de banco de dados ou servidor próprio.

---

## 14. Disclaimer técnico

Este projeto possui finalidade **exclusivamente educacional e demonstrativa**.

**Este app não implementa nenhuma verificação normativa** (NBR 6118, NBR 8681, NBR 8800, NBR 7190 ou qualquer outra). Realiza apenas estática elementar (equilíbrio de viga biapoiada com carga uniforme).

Os resultados apresentados:

* Não substituem a análise técnica de um engenheiro habilitado.
* Não constituem projeto estrutural.
* Não substituem a emissão de **ART** (Anotação de Responsabilidade Técnica) ou **RRT** (Registro de Responsabilidade Técnica).
* Não substituem qualquer responsabilidade técnica profissional.

Antes de aplicar qualquer resultado em obra real, reforma, laudo, orçamento ou tomada de decisão técnica, **é obrigatória a validação por profissional legalmente habilitado**, considerando as normas técnicas aplicáveis ao caso, condições reais de carregamento, materiais, vínculos, segurança estrutural e demais critérios de projeto.

---

## 15. Licença

* **Código:** MIT License (arquivo `LICENSE` na raiz do projeto).
* **Conteúdo educacional do README e materiais associados:** CC-BY 4.0.
