# --- Correção para compatibilidade com Python 3.13+ ---
import pkgutil
import importlib.util
if not hasattr(pkgutil, "find_loader"):
    pkgutil.find_loader = importlib.util.find_spec
# ------------------------------------------------------

from dash import Dash, html, dcc, Input, Output
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go

# ------------------ CONFIGURAÇÕES ------------------
DB_CONFIG = {
    "dbname": "neondb",
    "user": "neondb_owner",
    "password": "npg_oktJBnQv8Er4",
    "host": "ep-bitter-silence-acfj6gdd-pooler.sa-east-1.aws.neon.tech",
    "port": "5432",
    "sslmode": "require"
}

# ------------------ FUNÇÃO PARA CARREGAR DADOS ------------------
def carregar_dados():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        query = """
            SELECT id, ean, sku, descricao, chassi, montador,
                   data_inicio, data_fim, status,
                   EXTRACT(EPOCH FROM (data_fim - data_inicio))/60 AS tempo_minutos
            FROM producao
            ORDER BY data_inicio DESC;
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            print("⚠️ Nenhum registro encontrado na tabela producao.")
        else:
            df["data_inicio"] = pd.to_datetime(df["data_inicio"])
            df["data_fim"] = pd.to_datetime(df["data_fim"])
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return pd.DataFrame()

# ------------------ INICIALIZAÇÃO DO DASH ------------------
app = Dash(__name__)
app.title = "Dashboard de Produção"

# ------------------ LAYOUT ------------------
app.layout = html.Div([
    html.H1("📊 Dashboard de Produção", style={"textAlign": "center"}),

    html.Div([
        html.Button("🔄 Atualizar Dados", id="btn-atualizar", n_clicks=0, style={"marginBottom": "10px"}),
    ], style={"textAlign": "center"}),

    dcc.Dropdown(id="filtro_montador", placeholder="Filtrar por Montador", style={"width": "50%", "margin": "auto"}),

    html.Div([
        dcc.Graph(id="grafico_por_sku", style={"width": "48%", "display": "inline-block"}),
        dcc.Graph(id="grafico_por_montador", style={"width": "48%", "display": "inline-block"})
    ]),
    html.Div([
        dcc.Graph(id="grafico_tempo_medio", style={"width": "98%", "margin": "auto"})
    ]),
    html.Hr(),
    html.H3("📋 Tabela de Produção"),
    html.Div(id="tabela_producao")
])

# ------------------ CALLBACKS ------------------
@app.callback(
    [Output("grafico_por_sku", "figure"),
     Output("grafico_por_montador", "figure"),
     Output("grafico_tempo_medio", "figure"),
     Output("tabela_producao", "children"),
     Output("filtro_montador", "options")],
    [Input("btn-atualizar", "n_clicks"),
     Input("filtro_montador", "value")]
)
def atualizar_dashboard(n_clicks, filtro_montador):
    df = carregar_dados()
    if df.empty:
        fig_vazio = go.Figure()
        fig_vazio.update_layout(title="Sem dados disponíveis")
        return fig_vazio, fig_vazio, fig_vazio, html.P("Sem registros disponíveis."), []

    if filtro_montador:
        df = df[df["montador"] == filtro_montador]

    # --- Gráfico 1: Produção por SKU ---
    fig_sku = px.bar(
        df.groupby("sku")["id"].count().reset_index().rename(columns={"id": "Quantidade"}),
        x="sku", y="Quantidade", color="sku", text="Quantidade",
        title="Produção por SKU"
    )
    fig_sku.update_traces(textposition="outside")

    # --- Gráfico 2: Produção por Montador ---
    fig_montador = px.bar(
        df.groupby("montador")["id"].count().reset_index().rename(columns={"id": "Quantidade"}),
        x="montador", y="Quantidade", color="montador", text="Quantidade",
        title="Produção por Montador"
    )
    fig_montador.update_traces(textposition="outside")

    # --- Gráfico 3: Tempo médio de montagem ---
    df_tempo = df.dropna(subset=["tempo_minutos"])
    fig_tempo = px.box(
        df_tempo, x="montador", y="tempo_minutos", color="montador",
        title="Tempo de Montagem (minutos)"
    )

    # --- Opções do Dropdown ---
    opcoes_montadores = [{"label": m, "value": m} for m in sorted(df["montador"].dropna().unique())]

    # --- Tabela de produção ---
    tabela_html = html.Table([
        html.Thead(html.Tr([html.Th(col) for col in df.columns])),
        html.Tbody([
            html.Tr([
                html.Td(df.iloc[i][col]) for col in df.columns
            ]) for i in range(len(df))
        ])
    ], style={"width": "100%", "border": "1px solid #ccc", "fontSize": "12px"})

    return fig_sku, fig_montador, fig_tempo, tabela_html, opcoes_montadores


# ------------------ EXECUÇÃO ------------------
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
