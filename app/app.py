import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import folium
from folium import Choropleth, GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium

# ----------------------------
# Configuración de página
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

# Mayúsculas para consistencia
df['barrio_localizacion'] = df['barrio_localizacion'].str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.upper()

# Filtrar valores no válidos
no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA',
              'FUERA DE VALÈNCIA', 'EN DEPENDENCIAS MUNICIPALES']
df = df[
    (~df['distrito_localizacion'].isin(no_validos)) &
    (~df['barrio_localizacion'].isin(no_validos))
]

# ----------------------------
# Cargar GeoJSON
# ----------------------------
with open("./app/data/barris-barrios.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# ----------------------------
# Contar incidencias por barrio
# ----------------------------
conteo_barrios = df['barrio_localizacion'].value_counts().reset_index()
conteo_barrios.columns = ['nombre', 'conteo']
conteo_barrios['nombre'] = conteo_barrios['nombre'].astype(str)
conteo_barrios['conteo'] = conteo_barrios['conteo'].astype(int)

# Crear diccionario de conteo
conteo_dict = dict(zip(conteo_barrios['nombre'], conteo_barrios['conteo']))

# ----------------------------
# Limpiar y preparar GeoJSON (evitar errores de serialización)
# ----------------------------
for feature in geojson_data['features']:
    props = feature['properties']
    nombre = str(props.get('nombre', '')).upper()

    poblacion = props.get('poblacion', 1)
    try:
        poblacion = int(poblacion) if poblacion not in [None, '', 'NA'] else 1
    except:
        poblacion = 1

    conteo = conteo_dict.get(nombre, 0)
    try:
        conteo = int(conteo)
    except:
        conteo = 0

    props['nombre'] = str(nombre)
    props['poblacion'] = int(poblacion)
    props['conteo'] = int(conteo)
    props['incidencias_per_1000hab'] = round(conteo / poblacion * 1000, 2) if poblacion > 0 else 0.0

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
    tooltip=GeoJsonTooltip(
        fields=["nombre", "conteo", "incidencias_per_1000hab"],
        aliases=["Barrio", "Incidencias", "Incidencias por 1000 hab."],
        localize=True
    )
).add_to(m)

# ✅ Renderizar mapa
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
