
import subprocess
import sys



import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import plotly.graph_objs as go
import streamlit as st

# ------------ FUNCIÓN PARA PREPARAR LOS DATOS ------------------
def construir_df_prophet(df, tema='TODOS', barrio='TODOS'):
    df_filtrado = df.copy()
    if tema != 'TODOS':
        df_filtrado = df_filtrado[df_filtrado['tema'] == tema]
    if barrio != 'TODOS':
        df_filtrado = df_filtrado[df_filtrado['barrio_localizacion'] == barrio]

    df_filtrado = df_filtrado.set_index('fecha_entrada_ayuntamiento')
    df_agg = df_filtrado.resample('MS').size().reset_index(name='y')
    df_agg.rename(columns={'fecha_entrada_ayuntamiento': 'ds'}, inplace=True)
    return df_agg

# ------------ FUNCIÓN PRINCIPAL DE PRONÓSTICO ------------------
def ejecutar_forecast(df, tema='TODOS', barrio='TODOS', periodos_pred=6, test_size=6):
    df_prophet = construir_df_prophet(df, tema=tema, barrio=barrio)

    if df_prophet.shape[0] < test_size + 2:
        st.error("❌ No hay suficientes datos para entrenar y evaluar.")
        return

    df_train = df_prophet.iloc[:-test_size]
    df_test = df_prophet.iloc[-test_size:]

    modelo = Prophet()
    modelo.fit(df_train)

    future = modelo.make_future_dataframe(periods=periodos_pred, freq='MS')
    forecast = modelo.predict(future)

    forecast[['yhat', 'yhat_lower', 'yhat_upper']] = forecast[['yhat', 'yhat_lower', 'yhat_upper']].clip(lower=0)

    # ------------------ MÉTRICAS ------------------
    forecast_eval = forecast.set_index('ds').loc[df_test['ds']]
    y_true = df_test['y'].values
    y_pred = forecast_eval['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100



    # ------------------ GRÁFICO INTERACTIVO ------------------
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df_prophet['ds'], y=df_prophet['y'],
                             mode='lines+markers', name='Datos reales',
                             line=dict(color='black')))

    cutoff = df_prophet['ds'].iloc[-1]
    forecast_historico = forecast[forecast['ds'] <= cutoff]
    forecast_futuro = forecast[forecast['ds'] > cutoff]

    fig.add_trace(go.Scatter(x=forecast_historico['ds'], y=forecast_historico['yhat'],
                             mode='lines', name='Predicción histórica',
                             line=dict(color='blue', dash='dash')))

    if not forecast_futuro.empty:
        punto_conexion = forecast_historico.iloc[[-1]]
        futuro_conectado = pd.concat([punto_conexion, forecast_futuro])
        fig.add_trace(go.Scatter(x=futuro_conectado['ds'], y=futuro_conectado['yhat'],
                                 mode='lines', name='Predicción futura',
                                 line=dict(color='green', dash='dash')))

    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'],
                             mode='lines', line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'],
                             mode='lines', name='Intervalo inferior',
                             fill='tonexty', fillcolor='rgba(173,216,230,0.2)',
                             line=dict(width=0), showlegend=True))

    fig.update_layout(title=dict(text=f"Predicción de incidencias sobre {tema} en {barrio} ",
                                 font=dict(size=22)),
                      xaxis=dict(title='Fecha', titlefont=dict(size=16)),
                      yaxis=dict(title='Número de incidencias', titlefont=dict(size=16)),
                      hovermode='x unified',
                      template='plotly_white',
                      height=750)

    st.plotly_chart(fig, use_container_width=True)

# ----------- "WIDGETS" ADAPTADOS A STREAMLIT ------------------
def iniciar_forecast_interactivo(df):
    st.markdown("###  Predicción de incidencias")
    
    periodos_slider = st.slider("Periodos a predecir", min_value=1, max_value=24, value=6)
    tema_dropdown = st.selectbox("Tema", options=['TODOS'] + sorted(df['tema'].dropna().unique()))
    barrio_dropdown = st.selectbox("Barrio", options=['TODOS'] + sorted(df['barrio_localizacion'].dropna().unique()))

    ejecutar_forecast(df, tema=tema_dropdown, barrio=barrio_dropdown, periodos_pred=periodos_slider)

# ---------- LLAMADA FINAL ----------
# (esto se pondría al final de la página de análisis temporal)
# df = ...  # carga previa
# iniciar_forecast_interactivo(df)

import pandas as pd

# Carga tus datos aquí
df = pd.read_csv("data/total-castellano.csv", sep=';')

df = df.drop(columns=['distrito_solicitante', 'barrio_solicitante'], errors='ignore')
df = df[df['barrio_localizacion'] != 'En dependencias municipales']

df['barrio_localizacion'] = df['barrio_localizacion'].str.strip().str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.strip().str.upper()

df['fecha_entrada_ayuntamiento'] = pd.to_datetime(df['fecha_entrada_ayuntamiento'], errors='coerce')
df = df.dropna(subset=['fecha_entrada_ayuntamiento'])
df = df.sort_values(by='fecha_entrada_ayuntamiento', ascending=False)

no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA', 'FUERA DE VALÈNCIA' 'EN DEPENDENCIAS MUNICIPALES']

# Filtrar el DataFrame para quedarte solo con filas válidas
df = df[
    (~df['distrito_localizacion'].isin(no_validos)) &
    (~df['barrio_localizacion'].isin(no_validos))
]

# Ejecuta la app
iniciar_forecast_interactivo(df)
