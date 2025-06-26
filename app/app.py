import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
#import folium
#from folium import Choropleth, GeoJson, GeoJsonTooltip
#from streamlit_folium import st_folium

# ----------------------------
# Configuración de página (debe ir justo después de los imports)
# ----------------------------
st.set_page_config(page_title="Incidencias en Valencia", layout="wide")

st.title("📍 Análisis Exploratorio de Incidencias Urbanas en Valencia")
st.markdown("""
Esta sección presenta un análisis exploratorio de los datos de incidencias ciudadanas en Valencia.
""")

# ----------------------------
# Cargar datos
# ----------------------------
df = pd.read_csv("./app/data/total-castellano.csv", sep=';')
df = df.drop(columns=['distrito_solicitante', 'barrio_solicitante'], errors='ignore')
df = df[df['barrio_localizacion'] != 'En dependencias municipales']

# Pasar a mayúsculas para consistencia
df['barrio_localizacion'] = df['barrio_localizacion'].str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.upper()

# Lista de valores no válidos
no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA', 'FUERA DE VALÈNCIA', 'EN DEPENDENCIAS MUNICIPALES']

# Filtrar el DataFrame para quedarte solo con filas válidas
df = df[
    (~df['distrito_localizacion'].isin(no_validos)) &
    (~df['barrio_localizacion'].isin(no_validos))
]

# ----------------------------
# Cargar GeoJSON de barrios (sin geopandas)
# ----------------------------
with open("./app/data/barris-barrios.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# Normalizar propiedades del geojson para acceso fácil
for feature in geojson_data['features']:
    feature['properties']['nombre'] = feature['properties']['nombre'].upper()
    if 'poblacion' not in feature['properties']:
        feature['properties']['poblacion'] = 1  # evitar división por cero

# ----------------------------
# Contar incidencias por barrio
# ----------------------------
conteo_barrios = df['barrio_localizacion'].value_counts().reset_index()
conteo_barrios.columns = ['nombre', 'conteo']

# Crear un diccionario de conteos para unir con geojson
conteo_dict = dict(zip(conteo_barrios['nombre'], conteo_barrios['conteo']))

# Añadir conteo y tasa por 1000 habitantes a cada barrio
for feature in geojson_data['features']:
    nombre = feature['properties']['nombre']
    conteo = conteo_dict.get(nombre, 0)
    poblacion = feature['properties'].get('poblacion', 1)
    feature['properties']['conteo'] = conteo
    feature['properties']['incidencias_per_1000hab'] = (conteo / poblacion * 1000) if poblacion > 0 else 0

# ----------------------------
# Mapa Interactivo
# ----------------------------
st.subheader("🌍 Mapa interactivo de incidencias por barrio")

m = folium.Map(location=[39.47, -0.38], zoom_start=12)

Choropleth(
    geo_data=geojson_data,
    data=conteo_barrios,
    columns=["nombre", "conteo"],
    key_on="feature.properties.nombre",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Número de incidencias"
).add_to(m)

GeoJson(
    geojson_data,
    tooltip=GeoJsonTooltip(fields=["nombre", "conteo"], aliases=["Barrio", "Incidencias"])
).add_to(m)

st_folium(m, width=1000, height=500)

# ----------------------------
# Gráfico de tarta
# ----------------------------
st.subheader("🥧 Distribución de incidencias por tipo (Tema)")

tema_counts = df['tema'].value_counts()
fig2, ax2 = plt.subplots(figsize=(7, 7))
ax2.pie(tema_counts, labels=tema_counts.index, autopct='%1.1f%%', startangle=90)
ax2.axis('equal')
st.pyplot(fig2)
