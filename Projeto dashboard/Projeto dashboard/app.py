from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html

BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_FILE = BASE_DIR / "lifestyle weight tracker.csv"
FALLBACK_DATA_FILE = BASE_DIR / "dataset_tratado2.csv"

COLOR_PRIMARY = "#0F766E"
COLOR_SECONDARY = "#D97706"
COLOR_ACCENT = "#1D4ED8"
COLOR_SURFACE = "#FFFDF8"
COLOR_TEXT = "#172026"
COLOR_MUTED = "#5B6470"
COLOR_GRID = "rgba(23, 32, 38, 0.10)"
PLOT_BG = "#FFFDF8"
FONT_FAMILY = "Georgia, Cambria, 'Times New Roman', serif"

WORKOUT_COLORS = {
    "Sem treino": "#94A3B8",
    "Cardio": "#0F766E",
    "Strength": "#D97706",
    "Yoga": "#7C3AED",
}

TABLE_COLUMNS = [
    "User_ID",
    "Gender",
    "Age",
    "Workout_Type",
    "Workout_Intensity",
    "Calories_Consumed",
    "Steps",
    "Sleep_Hours",
    "Stress_Level",
    "Weight_Change",
]

CORR_COLUMNS = [
    "Age",
    "Sleep_Hours",
    "Stress_Level",
    "Calories_Consumed",
    "Protein_g",
    "Carbs_g",
    "Fat_g",
    "Steps",
    "Workout_Intensity",
    "Temp_C",
    "Weight_Change",
]


def formatar_inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def formatar_decimal(valor: float, casas: int = 3) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def criar_template() -> go.layout.Template:
    template = go.layout.Template()
    template.layout = go.Layout(
        font={"family": FONT_FAMILY, "color": COLOR_TEXT},
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        title={"font": {"size": 21, "color": COLOR_TEXT}},
        xaxis={"gridcolor": COLOR_GRID, "linecolor": COLOR_GRID, "zerolinecolor": COLOR_GRID},
        yaxis={"gridcolor": COLOR_GRID, "linecolor": COLOR_GRID, "zerolinecolor": COLOR_GRID},
        legend={
            "bgcolor": "rgba(255,255,255,0.72)",
            "bordercolor": "rgba(15, 118, 110, 0.12)",
            "borderwidth": 1,
        },
        margin={"l": 80, "r": 40, "t": 80, "b": 60},
    )
    return template


def aplicar_estilo_figura(fig: go.Figure) -> go.Figure:
    fig.update_layout(template=APP_TEMPLATE)
    # Garante que os eixos se ajustem automaticamente ao tamanho do texto
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def figura_vazia(titulo: str, mensagem: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=mensagem,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": COLOR_MUTED, "family": FONT_FAMILY},
    )
    fig.update_layout(
        template=APP_TEMPLATE,
        title=titulo,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def card_kpi(titulo: str, elemento_id: str, destaque: str) -> html.Div:
    return html.Div(
        [
            html.P(titulo, style={"margin": "0", "color": COLOR_MUTED, "fontSize": "0.95rem"}),
            html.H3(
                id=elemento_id,
                style={"margin": "8px 0 0 0", "fontSize": "2rem", "color": destaque, "fontWeight": "700"},
            ),
        ],
        style=KPI_CARD_STYLE,
    )


def carregar_base_bruta() -> pd.DataFrame:
    if RAW_DATA_FILE.exists():
        return pd.read_csv(RAW_DATA_FILE)
    return pd.read_csv(FALLBACK_DATA_FILE)


def aplicar_tratamentos(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = data.copy()
    relatorio = {}

    numericas = [
        "Age",
        "Stress_Level",
        "Sleep_Hours",
        "Calories_Consumed",
        "Protein_g",
        "Carbs_g",
        "Fat_g",
        "Steps",
        "Workout_Intensity",
        "Temp_C",
        "Weight_Change",
        "Current_Weight_kg",
        "Height_cm",
    ]
    for col in numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    relatorio["missing_total_antes"] = int(df.isna().sum().sum())
    relatorio["workout_ausente_antes"] = int(df["Workout_Type"].isna().sum()) if "Workout_Type" in df else 0
    relatorio["calorias_ausente_antes"] = int(df["Calories_Consumed"].isna().sum()) if "Calories_Consumed" in df else 0
    relatorio["calorias_negativas_antes"] = int((df["Calories_Consumed"] < 0).sum()) if "Calories_Consumed" in df else 0
    relatorio["steps_negativos_antes"] = int((df["Steps"] < 0).sum()) if "Steps" in df else 0

    if "Workout_Type" in df.columns:
        df["Workout_Type"] = df["Workout_Type"].fillna("Sem treino")

    if "Calories_Consumed" in df.columns:
        mediana_calorias = df.loc[df["Calories_Consumed"] >= 0, "Calories_Consumed"].median()
        df.loc[df["Calories_Consumed"] < 0, "Calories_Consumed"] = pd.NA
        df["Calories_Consumed"] = df["Calories_Consumed"].fillna(mediana_calorias)

    if "Steps" in df.columns:
        df["Steps"] = df["Steps"].clip(lower=0)
        df["Steps"] = df["Steps"].fillna(df["Steps"].median())

    for col in ["Protein_g", "Carbs_g", "Fat_g", "Sleep_Hours", "Stress_Level", "Workout_Intensity"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].fillna("Nao informado")

    if {"Workout_Type", "Workout_Intensity"}.issubset(df.columns):
        sem_treino = df["Workout_Type"] == "Sem treino"
        df.loc[sem_treino, "Workout_Intensity"] = df.loc[sem_treino, "Workout_Intensity"].fillna(0)

    df["Faixa_Etaria"] = pd.cut(
        df["Age"],
        bins=[17, 25, 35, 45, 55, 65],
        labels=["18-25", "26-35", "36-45", "46-55", "56-65"],
        include_lowest=True,
    )
    df["Perfil_Sono"] = pd.cut(
        df["Sleep_Hours"],
        bins=[0, 5, 7, 9, 24],
        labels=["Baixo sono", "Sono moderado", "Sono adequado", "Sono elevado"],
        include_lowest=True,
    )

    if {"Current_Weight_kg", "Height_cm"}.issubset(df.columns):
        altura_m = df["Height_cm"] / 100
        df["IMC"] = df["Current_Weight_kg"] / (altura_m**2)
        df["Categoria_IMC"] = pd.cut(
            df["IMC"],
            bins=[0, 18.5, 25, 30, 100],
            labels=["Abaixo", "Normal", "Sobrepeso", "Obesidade"],
            include_lowest=True,
        )

    relatorio["missing_total_depois"] = int(df.isna().sum().sum())
    relatorio["workout_ausente_depois"] = int(df["Workout_Type"].isna().sum())
    relatorio["calorias_ausente_depois"] = int(df["Calories_Consumed"].isna().sum())
    relatorio["calorias_negativas_depois"] = int((df["Calories_Consumed"] < 0).sum())
    relatorio["steps_negativos_depois"] = int((df["Steps"] < 0).sum())

    return df, relatorio


def criar_relatorio_missing(df_antes: pd.DataFrame, df_depois: pd.DataFrame) -> pd.DataFrame:
    missing_antes = df_antes.isna().sum()
    missing_depois = df_depois.isna().sum().reindex(missing_antes.index, fill_value=0)
    relatorio = pd.DataFrame(
        {
            "Coluna": missing_antes.index,
            "Ausentes_antes": missing_antes.values,
            "Ausentes_depois": missing_depois.values,
        }
    )
    relatorio = relatorio[(relatorio["Ausentes_antes"] > 0) | (relatorio["Ausentes_depois"] > 0)]
    if relatorio.empty:
        relatorio = pd.DataFrame(
            {"Coluna": ["Sem colunas com ausentes"], "Ausentes_antes": [0], "Ausentes_depois": [0]}
        )
    return relatorio.sort_values("Ausentes_antes", ascending=False)


def criar_figura_qualidade(relatorio_missing: pd.DataFrame) -> go.Figure:
    base = relatorio_missing.melt(
        id_vars="Coluna",
        value_vars=["Ausentes_antes", "Ausentes_depois"],
        var_name="Etapa",
        value_name="Qtd_Ausentes",
    )
    base["Etapa"] = base["Etapa"].replace(
        {"Ausentes_antes": "Antes do tratamento", "Ausentes_depois": "Depois do tratamento"}
    )

    fig = px.bar(
        base,
        x="Coluna",
        y="Qtd_Ausentes",
        color="Etapa",
        barmode="group",
        title="Controle de qualidade: valores ausentes antes e depois",
        labels={"Coluna": "Variável", "Qtd_Ausentes": "Quantidade de ausentes"},
        color_discrete_map={"Antes do tratamento": "#DC2626", "Depois do tratamento": "#0F766E"},
    )
    fig.update_xaxes(tickangle=-25)
    return aplicar_estilo_figura(fig)


def filtrar_base(
    data: pd.DataFrame,
    generos: list[str] | None,
    treinos: list[str] | None,
    faixa_idade: list[int],
    faixa_intensidade: list[int],
    perfis_sono: list[str] | None,
) -> pd.DataFrame:
    generos_ativos = generos or GENDER_OPTIONS
    treinos_ativos = treinos or WORKOUT_OPTIONS
    sono_ativos = perfis_sono or SONO_OPTIONS

    filtro = (
        data["Gender"].isin(generos_ativos)
        & data["Workout_Type"].isin(treinos_ativos)
        & data["Perfil_Sono"].astype(str).isin(sono_ativos)
        & data["Age"].between(faixa_idade[0], faixa_idade[1])
        & data["Workout_Intensity"].between(faixa_intensidade[0], faixa_intensidade[1])
    )
    return data.loc[filtro].copy()


def preparar_tabela(dff: pd.DataFrame) -> list[dict]:
    tabela = dff[TABLE_COLUMNS].copy()
    for col in tabela.columns:
        if str(tabela[col].dtype) == "category":
            tabela[col] = tabela[col].astype(str)
    tabela = tabela.sort_values("Weight_Change", ascending=False).head(14).round(3)
    return tabela.to_dict("records")


df_raw = carregar_base_bruta()
df, treatment_report = aplicar_tratamentos(df_raw)
APP_TEMPLATE = criar_template()
QUALITY_REPORT = criar_relatorio_missing(df_raw, df)
QUALITY_FIGURE = criar_figura_qualidade(QUALITY_REPORT)

AGE_MIN = int(df["Age"].min())
AGE_MAX = int(df["Age"].max())
INTENSITY_MIN = int(df["Workout_Intensity"].min())
INTENSITY_MAX = int(df["Workout_Intensity"].max())

AGE_MARKS = {idade: str(idade) for idade in range(AGE_MIN, AGE_MAX + 1, 10)}
AGE_MARKS.setdefault(AGE_MAX, str(AGE_MAX))
INTENSITY_MARKS = {i: str(i) for i in range(INTENSITY_MIN, INTENSITY_MAX + 1)}

GENDER_OPTIONS = sorted(df["Gender"].dropna().unique())
WORKOUT_OPTIONS = sorted(df["Workout_Type"].dropna().unique())
SONO_OPTIONS = [str(c) for c in df["Perfil_Sono"].cat.categories if pd.notna(c)]

APP_STYLE = {
    "fontFamily": FONT_FAMILY,
    "background": "linear-gradient(180deg, #EEE8D8 0%, #F7F4ED 22%, #F9F7F1 100%)",
    "minHeight": "100vh",
    "padding": "28px 18px 40px",
    "color": COLOR_TEXT,
    "maxWidth": "1360px",
    "margin": "0 auto",
}

HERO_STYLE = {
    "background": "linear-gradient(135deg, rgba(15,118,110,0.96), rgba(17,24,39,0.96))",
    "borderRadius": "28px",
    "padding": "32px",
    "color": "#F8FAFC",
    "boxShadow": "0 22px 48px rgba(15, 23, 42, 0.22)",
    "marginBottom": "22px",
}

SECTION_CARD_STYLE = {
    "backgroundColor": COLOR_SURFACE,
    "borderRadius": "22px",
    "padding": "22px",
    "boxShadow": "0 12px 30px rgba(15, 23, 42, 0.08)",
    "border": "1px solid rgba(148, 163, 184, 0.14)",
    "marginBottom": "20px",
}

KPI_CARD_STYLE = {
    "background": "linear-gradient(180deg, rgba(255,253,248,1) 0%, rgba(247,244,237,1) 100%)",
    "borderRadius": "18px",
    "padding": "18px",
    "border": "1px solid rgba(15, 118, 110, 0.12)",
    "boxShadow": "0 10px 24px rgba(15, 23, 42, 0.06)",
    "minWidth": "220px",
    "flex": "1 1 220px",
}

GRAPH_CARD_STYLE = {
    "backgroundColor": COLOR_SURFACE,
    "borderRadius": "18px",
    "padding": "12px 12px 2px",
    "boxShadow": "0 10px 22px rgba(15, 23, 42, 0.06)",
    "border": "1px solid rgba(148, 163, 184, 0.12)",
}

NOTE_CARD_STYLE = {
    "background": "rgba(255,255,255,0.55)",
    "borderLeft": f"5px solid {COLOR_SECONDARY}",
    "padding": "14px 16px",
    "borderRadius": "12px",
    "color": COLOR_TEXT,
}

app = Dash(__name__)
app.title = "Dashboard | Lifestyle Weight Tracker"

app.layout = html.Div(
    [
        html.Div(
            [
                html.P(
                    "Projeto de Estatistica e Probabilidade",
                    style={
                        "textTransform": "uppercase",
                        "letterSpacing": "0.14em",
                        "fontSize": "0.8rem",
                        "margin": "0 0 10px 0",
                        "color": "#C7D2FE",
                    },
                ),
                html.H1("Dashboard analitico do Lifestyle Weight Tracker", style={"margin": "0 0 10px 0", "fontSize": "2.4rem"}),
                html.P(
                    "Painel interativo para explorar relacoes entre habitos de vida e variacao de peso, "
                    "com foco em qualidade dos dados, tratamentos e comunicacao de insights.",
                    style={"margin": "0", "maxWidth": "830px", "lineHeight": "1.65", "fontSize": "1.05rem", "color": "#E2E8F0"},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.P("Registros analisados", style={"margin": "0", "color": "#BFDBFE"}),
                                html.H3(f"{formatar_inteiro(len(df))} linhas", style={"margin": "6px 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            [
                                html.P("Variavel-alvo", style={"margin": "0", "color": "#BFDBFE"}),
                                html.H3("Weight_Change", style={"margin": "6px 0 0 0"}),
                            ]
                        ),
                        html.Div(
                            [
                                html.P("Pergunta central", style={"margin": "0", "color": "#BFDBFE"}),
                                html.H3("habitos x peso", style={"margin": "6px 0 0 0"}),
                            ]
                        ),
                    ],
                    style={
                        "display": "flex",
                        "gap": "24px",
                        "flexWrap": "wrap",
                        "marginTop": "24px",
                        "paddingTop": "18px",
                        "borderTop": "1px solid rgba(255,255,255,0.15)",
                    },
                ),
            ],
            style=HERO_STYLE,
        ),
        html.Div(
            [
                html.H3("Filtros interativos", style={"marginTop": "0", "marginBottom": "14px"}),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Genero", style={"fontWeight": "700"}),
                                dcc.Dropdown(
                                    id="filtro-genero",
                                    options=[{"label": g, "value": g} for g in GENDER_OPTIONS],
                                    value=GENDER_OPTIONS,
                                    multi=True,
                                    placeholder="Selecione genero(s)",
                                    style={"marginTop": "8px"},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "210px"},
                        ),
                        html.Div(
                            [
                                html.Label("Tipo de treino", style={"fontWeight": "700"}),
                                dcc.Dropdown(
                                    id="filtro-treino",
                                    options=[{"label": w, "value": w} for w in WORKOUT_OPTIONS],
                                    value=WORKOUT_OPTIONS,
                                    multi=True,
                                    placeholder="Selecione treino(s)",
                                    style={"marginTop": "8px"},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "210px"},
                        ),
                        html.Div(
                            [
                                html.Label("Perfil de sono", style={"fontWeight": "700"}),
                                dcc.Dropdown(
                                    id="filtro-sono",
                                    options=[{"label": s, "value": s} for s in SONO_OPTIONS],
                                    value=SONO_OPTIONS,
                                    multi=True,
                                    placeholder="Selecione perfil de sono",
                                    style={"marginTop": "8px"},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "210px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Faixa de idade", style={"fontWeight": "700"}),
                                dcc.RangeSlider(
                                    id="filtro-idade",
                                    min=AGE_MIN,
                                    max=AGE_MAX,
                                    step=1,
                                    value=[AGE_MIN, AGE_MAX],
                                    marks=AGE_MARKS,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "290px"},
                        ),
                        html.Div(
                            [
                                html.Label("Intensidade do treino", style={"fontWeight": "700"}),
                                dcc.RangeSlider(
                                    id="filtro-intensidade",
                                    min=INTENSITY_MIN,
                                    max=INTENSITY_MAX,
                                    step=1,
                                    value=[INTENSITY_MIN, INTENSITY_MAX],
                                    marks=INTENSITY_MARKS,
                                    tooltip={"placement": "bottom", "always_visible": False},
                                ),
                            ],
                            style={"flex": "1", "minWidth": "290px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "18px", "flexWrap": "wrap"},
                ),
            ],
            style=SECTION_CARD_STYLE,
        ),
        html.Div(
            [
                card_kpi("Registros filtrados", "kpi-total", COLOR_PRIMARY),
                card_kpi("Media de variacao de peso", "kpi-weight", COLOR_SECONDARY),
                card_kpi("Media de calorias consumidas", "kpi-calorias", COLOR_ACCENT),
                card_kpi("Media de passos", "kpi-steps", "#9333EA"),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "20px"},
        ),
        html.Div(
            [
                html.Div(dcc.Graph(id="grafico-dispersao"), style=GRAPH_CARD_STYLE),
                html.Div(dcc.Graph(id="grafico-box"), style=GRAPH_CARD_STYLE),
                html.Div(dcc.Graph(id="grafico-faixa"), style=GRAPH_CARD_STYLE),
                html.Div(dcc.Graph(id="grafico-correlacao"), style=GRAPH_CARD_STYLE),
                html.Div(dcc.Graph(id="grafico-sono"), style=GRAPH_CARD_STYLE),
                html.Div(dcc.Graph(id="grafico-correlacao-top"), style=GRAPH_CARD_STYLE),
            ],
            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))", "gap": "18px", "marginBottom": "20px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("Leituras do recorte filtrado", style={"marginTop": "0"}),
                        html.Div(id="texto-insights", style={"lineHeight": "1.8"}),
                    ],
                    style=SECTION_CARD_STYLE,
                ),
                html.Div(
                    [
                        html.H3("Qualidade dos dados e tratamentos aplicados", style={"marginTop": "0"}),
                        html.Ul(
                            [
                                html.Li(
                                    f"Workout_Type ausente: {formatar_inteiro(treatment_report['workout_ausente_antes'])} -> "
                                    f"{formatar_inteiro(treatment_report['workout_ausente_depois'])} (preenchido como 'Sem treino')."
                                ),
                                html.Li(
                                    f"Calories_Consumed ausente: {formatar_inteiro(treatment_report['calorias_ausente_antes'])} -> "
                                    f"{formatar_inteiro(treatment_report['calorias_ausente_depois'])} (imputacao por mediana)."
                                ),
                                html.Li(
                                    f"Calories_Consumed negativo: {formatar_inteiro(treatment_report['calorias_negativas_antes'])} -> "
                                    f"{formatar_inteiro(treatment_report['calorias_negativas_depois'])}."
                                ),
                                html.Li(
                                    f"Steps negativo: {formatar_inteiro(treatment_report['steps_negativos_antes'])} -> "
                                    f"{formatar_inteiro(treatment_report['steps_negativos_depois'])}."
                                ),
                            ],
                            style={"paddingLeft": "20px", "lineHeight": "1.7", "marginBottom": "12px"},
                        ),
                        dcc.Graph(figure=QUALITY_FIGURE, id="grafico-qualidade"),
                    ],
                    style=SECTION_CARD_STYLE,
                ),
            ],
            style={"display": "grid", "gridTemplateColumns": "minmax(320px, 1fr) minmax(320px, 1fr)", "gap": "20px"},
        ),
        html.Div(
            [
                html.H3("Amostra do recorte filtrado", style={"marginTop": "0"}),
                html.P(
                    "Use esta tabela para mostrar exemplos reais durante a apresentacao. "
                    "O botao abaixo exporta exatamente o recorte selecionado nos filtros.",
                    style={"marginTop": "0", "color": COLOR_MUTED},
                ),
                dash_table.DataTable(
                    id="tabela-amostra",
                    columns=[{"name": c, "id": c} for c in TABLE_COLUMNS],
                    data=[],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"padding": "8px", "fontFamily": FONT_FAMILY, "fontSize": "0.92rem"},
                    style_header={"fontWeight": "700", "backgroundColor": "#EEF2FF"},
                ),
                html.Div(
                    [
                        html.Button(
                            "Baixar recorte filtrado (CSV)",
                            id="btn-download",
                            n_clicks=0,
                            style={
                                "marginTop": "14px",
                                "backgroundColor": COLOR_PRIMARY,
                                "color": "#FFFFFF",
                                "border": "none",
                                "borderRadius": "10px",
                                "padding": "10px 16px",
                                "cursor": "pointer",
                                "fontWeight": "700",
                            },
                        )
                    ]
                ),
            ],
            style=SECTION_CARD_STYLE,
        ),
        dcc.Download(id="download-dados"),
    ],
    style=APP_STYLE,
)


@app.callback(
    Output("kpi-total", "children"),
    Output("kpi-weight", "children"),
    Output("kpi-calorias", "children"),
    Output("kpi-steps", "children"),
    Output("grafico-dispersao", "figure"),
    Output("grafico-box", "figure"),
    Output("grafico-faixa", "figure"),
    Output("grafico-correlacao", "figure"),
    Output("grafico-sono", "figure"),
    Output("grafico-correlacao-top", "figure"),
    Output("texto-insights", "children"),
    Output("tabela-amostra", "data"),
    Input("filtro-genero", "value"),
    Input("filtro-treino", "value"),
    Input("filtro-idade", "value"),
    Input("filtro-intensidade", "value"),
    Input("filtro-sono", "value"),
)
def atualizar_dashboard(generos, treinos, faixa_idade, faixa_intensidade, perfis_sono):
    dff = filtrar_base(df, generos, treinos, faixa_idade, faixa_intensidade, perfis_sono)

    if dff.empty:
        mensagem = "Sem dados para os filtros selecionados."
        return (
            "0",
            "0,000 kg",
            "0 kcal",
            "0 passos",
            figura_vazia("Calorias x variacao de peso", mensagem),
            figura_vazia("Distribuicao por tipo de treino", mensagem),
            figura_vazia("Media por faixa etaria e genero", mensagem),
            figura_vazia("Correlacao entre variaveis numericas", mensagem),
            figura_vazia("Perfil de sono x variacao de peso", mensagem),
            figura_vazia("Top correlacoes com Weight_Change", mensagem),
            html.Div(html.P(mensagem, style={"margin": "0", "color": COLOR_MUTED}), style=NOTE_CARD_STYLE),
            [],
        )

    total = formatar_inteiro(len(dff))
    media_weight = f"{formatar_decimal(dff['Weight_Change'].mean())} kg"
    media_calorias = f"{formatar_inteiro(round(dff['Calories_Consumed'].mean()))} kcal"
    media_steps = f"{formatar_inteiro(round(dff['Steps'].mean()))} passos"

    amostra = dff.sample(min(3500, len(dff)), random_state=42)

    fig_disp = px.scatter(
        amostra,
        x="Calories_Consumed",
        y="Weight_Change",
        color="Workout_Type",
        symbol="Gender",
        color_discrete_map=WORKOUT_COLORS,
        hover_data=["Age", "Sleep_Hours", "Steps", "Stress_Level"],
        opacity=0.72,
        title="Dispersao calorias consumidas variacao de peso",
        labels={"Calories_Consumed": "Calorias", "Weight_Change": "Variacao de peso"},
    )
    fig_disp.update_traces(marker={"size": 8, "line": {"width": 0.5, "color": "#FFFFFF"}})
    aplicar_estilo_figura(fig_disp)

    fig_box = px.box(
        dff,
        x="Workout_Type",
        y="Weight_Change",
        color="Workout_Type",
        color_discrete_map=WORKOUT_COLORS,
        points="suspectedoutliers",
        title="variacao de peso por tipo de treino",
        labels={"Workout_Type": "Tipo de treino", "Weight_Change": "Variacao de peso"},
    )
    fig_box.update_layout(showlegend=False)
    aplicar_estilo_figura(fig_box)

    faixa_genero = (
        dff.groupby(["Faixa_Etaria", "Gender"], observed=False)["Weight_Change"].mean().reset_index().dropna()
    )
    fig_faixa = px.bar(
        faixa_genero,
        x="Faixa_Etaria",
        y="Weight_Change",
        color="Gender",
        barmode="group",
        text_auto=".3f",
        title="Media variacao peso por faixa etaria e genero",
        labels={"Faixa_Etaria": "Faixa etaria", "Weight_Change": "Media de variacao de peso"},
        color_discrete_sequence=["#0F766E", "#1D4ED8", "#D97706"],
    )
    aplicar_estilo_figura(fig_faixa)

    corr_cols = [c for c in CORR_COLUMNS if c in dff.columns]
    corr = dff[corr_cols].corr(numeric_only=True).round(2)
    fig_corr = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=[[0.0, "#7F1D1D"], [0.5, "#F8FAFC"], [1.0, "#0F766E"]],
        zmin=-1,
        zmax=1,
        title="Mapa de correlacao entre variaveis numericas",
    )
    aplicar_estilo_figura(fig_corr)

    sono_media = dff.groupby("Perfil_Sono", observed=False)["Weight_Change"].mean().reset_index().dropna()
    fig_sono = px.violin(
        dff,
        x="Perfil_Sono",
        y="Weight_Change",
        color="Perfil_Sono",
        category_orders={"Perfil_Sono": SONO_OPTIONS},
        box=True,
        points=False,
        title="Perfil de sono distribuicao da variacao de peso",
        labels={"Perfil_Sono": "Perfil de sono", "Weight_Change": "Variacao de peso"},
        color_discrete_sequence=["#0F766E", "#1D4ED8", "#D97706", "#7C3AED"],
    )
    fig_sono.update_layout(showlegend=False)
    aplicar_estilo_figura(fig_sono)

    corr_peso = corr["Weight_Change"].drop("Weight_Change").dropna().sort_values(key=lambda s: s.abs(), ascending=False)
    top_corr = corr_peso.head(8).sort_values()
    top_corr_df = pd.DataFrame(
        {
            "Variavel": top_corr.index.str.replace("_", " "),
            "Correlacao": top_corr.values,
        }
    )
    fig_corr_top = px.bar(
        top_corr_df,
        x="Correlacao",
        y="Variavel",
        orientation="h",
        color="Correlacao",
        text_auto=".2f",
        title="correlacoes com Weight_Change",
        color_continuous_scale=[[0.0, "#7F1D1D"], [0.5, "#F8FAFC"], [1.0, "#0F766E"]],
    )
    aplicar_estilo_figura(fig_corr_top)

    destaque_positivo = corr_peso.sort_values(ascending=False).index[0].replace("_", " ")
    valor_positivo = corr_peso.sort_values(ascending=False).iloc[0]
    destaque_negativo = corr_peso.sort_values(ascending=True).index[0].replace("_", " ")
    valor_negativo = corr_peso.sort_values(ascending=True).iloc[0]

    treino_lider = dff.groupby("Workout_Type", observed=False)["Weight_Change"].mean().sort_values(ascending=False).index[0]
    sono_lider = sono_media.sort_values("Weight_Change", ascending=False).iloc[0]["Perfil_Sono"]
    faixa_lider = (
        dff.groupby("Faixa_Etaria", observed=False)["Weight_Change"].mean().dropna().sort_values(ascending=False).index[0]
    )

    insights = html.Div(
        [
            html.Div(
                html.P(
                    f"No recorte atual, a relacao positiva mais forte com Weight_Change aparece em {destaque_positivo} "
                    f"(r = {valor_positivo:.2f}) e a mais negativa em {destaque_negativo} (r = {valor_negativo:.2f}).",
                    style={"margin": "0"},
                ),
                style=NOTE_CARD_STYLE,
            ),
            html.P(
                f"O treino com maior media de Weight_Change e {treino_lider}; "
                f"o perfil de sono com maior media e {sono_lider}; e a faixa etaria lider e {faixa_lider}.",
                style={"margin": "14px 0 8px 0"},
            ),
            html.P(
                "A combinacao de dispersao, boxplot, violin e correlacao permite discutir "
                "relacao, distribuicao, comparacao de grupos e leitura multivariada.",
                style={"margin": "0 0 8px 0"},
            ),
            html.P(
                "Esses achados sao exploratorios: o dashboard mostra associacoes estatisticas, nao causalidade.",
                style={"margin": "0"},
            ),
        ]
    )

    dados_tabela = preparar_tabela(dff)

    return (
        total,
        media_weight,
        media_calorias,
        media_steps,
        fig_disp,
        fig_box,
        fig_faixa,
        fig_corr,
        fig_sono,
        fig_corr_top,
        insights,
        dados_tabela,
    )


@app.callback(
    Output("download-dados", "data"),
    Input("btn-download", "n_clicks"),
    State("filtro-genero", "value"),
    State("filtro-treino", "value"),
    State("filtro-idade", "value"),
    State("filtro-intensidade", "value"),
    State("filtro-sono", "value"),
    prevent_initial_call=True,
)
def baixar_recorte(n_clicks, generos, treinos, faixa_idade, faixa_intensidade, perfis_sono):
    dff = filtrar_base(df, generos, treinos, faixa_idade, faixa_intensidade, perfis_sono)
    nome_arquivo = f"recorte_dashboard_{len(dff)}_linhas.csv"
    return dcc.send_data_frame(dff.to_csv, nome_arquivo, index=False)


if __name__ == "__main__":
    app.run(debug=True)
