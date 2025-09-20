from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime, timedelta

app = Dash(__name__, external_stylesheets=[
    'https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap'
])
server = app.server  # Para Render/Gunicorn

# Contratos ROFEX (podes agregar más)
contratos = ['DLR/OCT25', 'DLR/NOV25', 'DLR/DEC25', 'DLR/JAN26']

# Función para obtener datos en tiempo real
def fetch_datos():
    try:
        # Dólar blue, CCL, MEP, A3500
        url = "https://criptoya.com/api/dolar"
        response = requests.get(url)
        data = response.json()
        dolares = {
            'Blue': data.get('blue', {}).get('price', 0),
            'CCL': data.get('ccl', {}).get('price', 0),
            'MEP': data.get('mep', {}).get('price', 0),
            'A3500': data.get('mayorista', {}).get('price', 0) * 1.65  # Ejemplo
        }
        # Tasas de caución (simuladas, usar API de Matba-Rofex si tenés acceso)
        tasas = {'Caucion 7d': 40.0, 'Caucion 30d': 42.0}  # En % anual
        return dolares, tasas
    except:
        return {'Blue': 0, 'CCL': 0, 'MEP': 0, 'A3500': 0}, {'Caucion 7d': 0, 'Caucion 30d': 0}

# Función para calcular días al vencimiento
def dias_vencimiento(contrato):
    mes_map = {'OCT25': '2025-10-31', 'NOV25': '2025-11-30', 'DEC25': '2025-12-31', 'JAN26': '2026-01-31'}
    vencimiento = datetime.strptime(mes_map.get(contrato, '2025-12-31'), '%Y-%m-%d')
    hoy = datetime.now()
    return (vencimiento - hoy).days

# Lógica de arbitraje (IA simple basada en reglas)
def detectar_arbitraje(futuro, contrato, dolares, tasas):
    dias = dias_vencimiento(contrato)
    if dias <= 0:
        return []
    
    señales = []
    for tipo, precio in dolares.items():
        if precio == 0:
            continue
        tna_implicita = ((futuro / precio - 1) * (360 / dias)) * 100
        # Comparar con tasa de caución promedio
        tasa_caucion = sum(tasas.values()) / len(tasas)
        
        if tna_implicita > tasa_caucion + 5:  # Margen de 5% para arbitraje
            señales.append(f"Arbitraje LARGO: Comprar {contrato} a {futuro}, vender {tipo} (TNA: {tna_implicita:.2f}%)")
        elif tna_implicita < tasa_caucion - 5:
            señales.append(f"Arbitraje CORTO: Vender {contrato} a {futuro}, comprar {tipo} (TNA: {tna_implicita:.2f}%)")
    
    return señales if señales else ["No hay oportunidades de arbitraje"]

# Estilo Lemon Cash
estilo = {
    'backgroundColor': '#1A1F2B',
    'color': '#FFFFFF',
    'fontFamily': 'Roboto, sans-serif',
    'padding': '20px',
    'maxWidth': '1200px',
    'margin': 'auto'
}
boton_estilo = {
    'backgroundColor': '#00D4B8',
    'color': '#1A1F2B',
    'border': 'none',
    'padding': '10px 20px',
    'fontSize': '16px',
    'borderRadius': '5px',
    'cursor': 'pointer'
}

# Layout
app.layout = html.Div([
    html.H1("Arbitraje Dólar Futuro ROFEX", style={'textAlign': 'center', 'color': '#00D4B8'}),
    html.Label("Seleccioná contrato ROFEX:", style={'fontSize': '18px', 'margin': '10px'}),
    dcc.Dropdown(
        id='contrato',
        options=[{'label': c, 'value': c} for c in contratos],
        value=contratos[0],
        style={'backgroundColor': '#2A2F3B', 'color': '#FFFFFF', 'marginBottom': '20px'}
    ),
    html.Label("Precio del futuro (ARS):", style={'fontSize': '18px', 'margin': '10px'}),
    dcc.Input(id='futuro', type='number', value=1600, style={'width': '200px', 'padding': '10px'}),
    html.Button("Calcular", id='calcular', style=boton_estilo),
    dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0),
    html.H2("Precios en Tiempo Real", style={'marginTop': '20px'}),
    dcc.Graph(id='dolar-graph'),
    html.H2("Tasas de Causión", style={'marginTop': '20px'}),
    html.Div(id='tasas-output'),
    html.H2("Oportunidades de Arbitraje", style={'marginTop': '20px', 'color': '#00D4B8'}),
    html.Div(id='arbitraje-output', style={'backgroundColor': '#2A2F3B', 'padding': '15px', 'borderRadius': '10px'})
], style=estilo)

# Callbacks
@app.callback(
    [Output('dolar-graph', 'figure'), Output('tasas-output', 'children'), Output('arbitraje-output', 'children')],
    [Input('interval-component', 'n_intervals'), Input('calcular', 'n_clicks')],
    [Input('contrato', 'value'), Input('futuro', 'value')]
)
def update_dashboard(n, n_clicks, contrato, futuro):
    dolares, tasas = fetch_datos()
    df = pd.DataFrame(list(dolares.items()), columns=['Tipo', 'Precio'])
    fig = px.bar(df, x='Tipo', y='Precio', title='Precios Dólar', 
                 color_discrete_sequence=['#00D4B8'], 
                 template='plotly_dark')
    
    tasas_text = [html.P(f"{k}: {v:.2f}%", style={'fontSize': '16px'}) for k, v in tasas.items()]
    
    if futuro and contrato:
        señales = detectar_arbitraje(futuro, contrato, dolares, tasas)
    else:
        señales = ["Ingresá un precio válido"]
    
    señales_text = [html.P(s, style={'fontSize': '16px', 'color': '#00D4B8'}) for s in señales]
    
    return fig, tasas_text, señales_text

if __name__ == '__main__':
    app.run_server(debug=True)
