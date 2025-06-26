import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import folium
from folium import Choropleth, GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Incidencias en Valencia", layout="wide")
st.title("\U0001F4CD Incidencias Urbanas en Valencia")

st.markdown("""
Bienvenido a la aplicación de **Incidencias Urbanas en Valencia**, una herramienta interactiva diseñada para explorar y entender el comportamiento de las incidencias reportadas por la ciudadanía en distintos barrios de la ciudad.  Gracias a esta plataforma, podrás visualizar los datos de manera intuitiva, filtrar por diferentes criterios y analizar tendencias espaciales y temporales que permiten identificar áreas con mayor carga de problemáticas urbanas.
""")

with st.expander("📍 ¿Qué encontrarás en esta aplicación?"):
    st.markdown("""
    Esta plataforma te permite:
    
    - Visualizar sobre el mapa las incidencias geolocalizadas por barrio  
    - Aplicar filtros personalizados por año, distrito, barrio, tema y subtema  
    - Observar rankings de barrios con más o menos incidencias  
    - Analizar la evolución mensual de incidencias a lo largo del tiempo  
    - Explorar la distribución temática con gráficos interactivos

    Todo esto con el objetivo de facilitar la interpretación y fomentar la toma de decisiones informadas sobre la gestión urbana.
    """)

with st.expander("📊 Sobre los datos utilizados"):
    st.markdown("""
    Los datos proceden de registros del Ayuntamiento de Valencia. Cada fila representa una incidencia urbana reportada, que incluye información sobre:

    - Fecha de entrada de la incidencia  
    - Tema principal y subtema asignado  
    - Barrio y distrito de localización  
    - Estado del expediente  

    La base de datos cubre un amplio rango de años (2020–2025) y contempla múltiples categorías: desde limpieza y jardinería, hasta ruidos, alumbrado, o trámites administrativos.
    """)

with st.expander("👥 ¿A quién está dirigida esta herramienta?"):
    st.markdown("""
    Esta aplicación puede ser útil para diferentes perfiles:

    - **Administración pública**: responsables de servicios urbanos o planificación  
    - **Analistas de datos**: que buscan patrones territoriales o temporales  
    - **Investigadores y estudiantes**: interesados en temas urbanos o datos abiertos  
    - **Ciudadanía activa**: con interés en conocer cómo evoluciona su entorno

    Su diseño busca equilibrio entre facilidad de uso y profundidad de análisis.
    """)

with st.expander("💡 Objetivos principales"):
    st.markdown("""
    - Fomentar la **transparencia** en la gestión municipal  
    - Detectar **zonas conflictivas o con necesidades especiales**  
    - Facilitar la comprensión de los **temas más recurrentes por zona**  
    - Proveer una herramienta accesible para el análisis urbano en Valencia
    """)



# ----------------------------
# Cargar datos
# ----------------------------
df = pd.read_csv("data/total-castellano.csv", sep=';')
df = df.drop(columns=['distrito_solicitante', 'barrio_solicitante'], errors='ignore')
df = df[df['barrio_localizacion'] != 'En dependencias municipales']
df['fecha_entrada_ayuntamiento'] = pd.to_datetime(df['fecha_entrada_ayuntamiento'], errors='coerce')
df['año'] = df['fecha_entrada_ayuntamiento'].dt.year

df['barrio_localizacion'] = df['barrio_localizacion'].str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.upper()

no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA', 'FUERA DE VALÈNCIA', 'EN DEPENDENCIAS MUNICIPALES']
df = df[(~df['distrito_localizacion'].isin(no_validos)) & (~df['barrio_localizacion'].isin(no_validos))]

# ----------------------------
# Cargar GeoDataFrame de barrios
# ----------------------------
gdf_barrios = gpd.read_file("data/barris-barrios.geojson")
gdf_barrios['nombre'] = gdf_barrios['nombre'].str.upper()

# ----------------------------
# Sidebar - Filtros
# ----------------------------
st.sidebar.title("\U0001F50D Filtros")

años = sorted(df['año'].dropna().unique())
año_sel = st.sidebar.slider("Selecciona rango de años", int(min(años)), int(max(años)), (int(min(años)), int(max(años))))

distritos = ['Todos'] + sorted(df['distrito_localizacion'].dropna().unique())
distrito_sel = st.sidebar.multiselect("Distrito", distritos, default=['Todos'])

barrios = ['Todos'] + sorted(df['barrio_localizacion'].dropna().unique())
barrio_sel = st.sidebar.multiselect("Barrio", barrios, default=['Todos'])

tipos = ['Todos'] + sorted(df['tema'].dropna().unique()) if 'tema' in df.columns else ['Todos']
tipo_sel = st.sidebar.selectbox("Tipo de incidencia", tipos)

subtipos = ['Todos'] + sorted(df['subtema'].dropna().unique()) if 'subtema' in df.columns else ['Todos']
subtipo_sel = st.sidebar.selectbox("Subtema", subtipos)


# ----------------------------
# Aplicar filtros
# ----------------------------
df_filt = df[(df['año'] >= año_sel[0]) & (df['año'] <= año_sel[1])].copy()

if 'Todos' not in distrito_sel:
    df_filt = df_filt[df_filt['distrito_localizacion'].isin(distrito_sel)]

if 'Todos' not in barrio_sel:
    df_filt = df_filt[df_filt['barrio_localizacion'].isin(barrio_sel)]

if tipo_sel != 'Todos' and 'tema' in df.columns:
    df_filt = df_filt[df_filt['tema'] == tipo_sel]

if subtipo_sel != 'Todos' and 'subtema' in df.columns:
    df_filt = df_filt[df_filt['subtema'] == subtipo_sel]



# ----------------------------
# Métricas clave
# ----------------------------

col1, col2, col3 = st.columns(3)
col1.metric("Total incidencias", len(df_filt))
col3.metric("Rango de años", f"{año_sel[0]} - {año_sel[1]}")

# ----------------------------
# Mapa Interactivo de Barrios
# ----------------------------
st.subheader("\U0001F30D Mapa interactivo de incidencias por barrio")

conteo_barrios_filt = df_filt['barrio_localizacion'].value_counts().reset_index()
conteo_barrios_filt.columns = ['nombre', 'conteo']

gdf_barrios_filt = gdf_barrios[['nombre', 'geometry']].copy()
gdf_barrios_filt = gdf_barrios_filt.merge(conteo_barrios_filt, on='nombre', how='left')
gdf_barrios_filt['conteo'] = gdf_barrios_filt['conteo'].fillna(0)

m = folium.Map(location=[39.47, -0.38], zoom_start=12)

folium.Choropleth(
    geo_data=gdf_barrios_filt,
    data=gdf_barrios_filt,
    columns=["nombre", "conteo"],
    key_on="feature.properties.nombre",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Número de incidencias"
).add_to(m)

GeoJson(
    gdf_barrios_filt,
    tooltip=GeoJsonTooltip(fields=["nombre", "conteo"], aliases=["Barrio", "Incidencias"])
).add_to(m)

st_folium(m, use_container_width=True, height=500)

# ----------------------------
# Ranking de barrios
# ----------------------------
st.subheader("\U0001F3C6 Rankings de barrios")

conteo = df_filt['barrio_localizacion'].value_counts().reset_index()
conteo.columns = ['barrio', 'conteo']

top = conteo.sort_values('conteo', ascending=False).head(5)
bottom = conteo.sort_values('conteo', ascending=True).head(5)

col1, col2 = st.columns(2)
col1.write("Top 5 barrios con más incidencias")
col1.dataframe(top)

col2.write("Top 5 barrios con menos incidencias")
col2.dataframe(bottom)

# ----------------------------
# Evolución temporal
# ----------------------------
st.subheader("\U0001F4C8 Evolución temporal de incidencias")

if 'fecha_entrada_ayuntamiento' in df_filt.columns:
    df_filt['fecha'] = pd.to_datetime(df_filt['fecha_entrada_ayuntamiento'], errors='coerce')
    df_time = df_filt.dropna(subset=['fecha']).copy()
    df_time['mes'] = df_time['fecha'].dt.to_period("M").astype(str)
    serie_mensual = df_time.groupby('mes').size().reset_index(name='incidencias')

    fig_time = px.line(serie_mensual, x='mes', y='incidencias', title='Incidencias por mes')
    st.plotly_chart(fig_time, use_container_width=True)
else:
    st.info("No se encontró la columna 'fecha_entrada_ayuntamiento' para mostrar la evolución temporal.")

# ----------------------------
# Gráfico de tarta por tema
# ----------------------------
st.subheader("\U0001F967 Distribución de incidencias por tipo (Tema)")

tema_counts = df_filt['tema'].value_counts()
tema_total = tema_counts.sum()

tema_agrupado = tema_counts[tema_counts / tema_total >= 0.06]
otros = tema_counts[tema_counts / tema_total < 0.06]

if not otros.empty:
    tema_agrupado["OTROS"] = otros.sum()

fig2, ax2 = plt.subplots(figsize=(7, 7))
ax2.pie(
    tema_agrupado,
    labels=tema_agrupado.index,
    autopct='%1.1f%%',
    startangle=90
)
ax2.axis('equal')
st.pyplot(fig2)
