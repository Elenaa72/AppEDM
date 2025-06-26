import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium import Choropleth, GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium

# Configuración de página
st.set_page_config(page_title="Incidencias en Valencia", layout="wide")
st.title("📍 Análisis Exploratorio de Incidencias Urbanas en Valencia")

st.markdown("""
Esta sección presenta un análisis exploratorio de los datos de incidencias ciudadanas en Valencia.
""")

# ----------------------------
# Cargar datos
# ----------------------------
df = pd.read_csv("data/total-castellano.csv", sep=';')
df = df.drop(columns=['distrito_solicitante', 'barrio_solicitante'], errors='ignore')
df = df[df['barrio_localizacion'] != 'En dependencias municipales']

# Pasar a mayúsculas para consistencia
df['barrio_localizacion'] = df['barrio_localizacion'].str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.upper()

# Lista de valores no válidos
no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA', 'FUERA DE VALÈNCIA' 'EN DEPENDENCIAS MUNICIPALES']

# Filtrar el DataFrame para quedarte solo con filas válidas
df = df[
    (~df['distrito_localizacion'].isin(no_validos)) &
    (~df['barrio_localizacion'].isin(no_validos))
]

# ----------------------------
# Cargar GeoDataFrame de barrios
# ----------------------------
gdf_barrios = gpd.read_file("data/barris-barrios.geojson")
gdf_barrios['nombre'] = gdf_barrios['nombre'].str.upper()

# Contar incidencias por barrio
conteo_barrios = df['barrio_localizacion'].value_counts().reset_index()
conteo_barrios.columns = ['nombre', 'conteo']

# Incidencias totales ya las tienes en gdf_barrios['conteo']
gdf_barrios['incidencias_per_1000hab'] = gdf_barrios['conteo'] / gdf_barrios['poblacion'] * 1000


# Unir al GeoDataFrame
gdf_barrios = gdf_barrios.merge(conteo_barrios, on='nombre', how='left')
gdf_barrios['conteo'] = gdf_barrios['conteo'].fillna(0)

gdf_barrios.to_file("data/barrios_enriquecido.geojson", driver="GeoJSON")


# ----------------------------
# Mapa Interactivo de Barrios
# ----------------------------
st.subheader("🌍 Mapa interactivo de incidencias por barrio")

m = folium.Map(location=[39.47, -0.38], zoom_start=12)

folium.Choropleth(
    geo_data=gdf_barrios,
    data=gdf_barrios,
    columns=["nombre", "conteo"],
    key_on="feature.properties.nombre",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Número de incidencias"
).add_to(m)

GeoJson(
    gdf_barrios,
    tooltip=GeoJsonTooltip(fields=["nombre", "conteo"], aliases=["Barrio", "Incidencias"])
).add_to(m)

st_folium(m, width=1000, height=500)



# ----------------------------
# Gráfico de tarta por tema
# ----------------------------

st.subheader("🥧 Distribución de incidencias por tipo (Tema)")

tema_counts = df['tema'].value_counts()
fig2, ax2 = plt.subplots(figsize=(7, 7))
ax2.pie(tema_counts, labels=tema_counts.index, autopct='%1.1f%%', startangle=90)
ax2.axis('equal')
st.pyplot(fig2)

