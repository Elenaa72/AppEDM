import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import folium
from folium import GeoJson, GeoJsonTooltip
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
import streamlit as st
import json

st.set_page_config(layout="wide")
st.title("Clustering de Barrios según Tipología de Incidencias")

st.markdown("""
Este apartado presenta un análisis **clustering** para agrupar los barrios de Valencia según el perfil temático de sus incidencias urbanas.  
Se utiliza el algoritmo K-Means para identificar patrones comunes entre barrios basados en la **distribución relativa de temas**, no en su volumen.

Gracias a este enfoque, se pueden detectar zonas que comparten problemáticas similares y adaptar la gestión pública a las necesidades específicas de cada grupo territorial.
""")

# --------- CARGA DE DATOS ---------
df = pd.read_csv("./app/data/total-castellano.csv", sep=';')
df = df.drop(columns=['distrito_solicitante', 'barrio_solicitante'], errors='ignore')
df = df[df['barrio_localizacion'] != 'En dependencias municipales']
df['fecha_entrada_ayuntamiento'] = pd.to_datetime(df['fecha_entrada_ayuntamiento'], errors='coerce')
df['año'] = df['fecha_entrada_ayuntamiento'].dt.year

df['barrio_localizacion'] = df['barrio_localizacion'].str.upper()
df['distrito_localizacion'] = df['distrito_localizacion'].str.upper()

no_validos = ['NO CONSTA', 'NO HI CONSTA', 'FORA DE VALÈNCIA', 'FORA  DE VALÈNCIA', 'FUERA DE VALÈNCIA', 'EN DEPENDENCIAS MUNICIPALES']
df = df[(~df['distrito_localizacion'].isin(no_validos)) & (~df['barrio_localizacion'].isin(no_validos))]

# --------- PREPROCESAMIENTO ---------
df_barrios = df.copy()
df_barrios['n'] = 1

tabla = df_barrios.pivot_table(
    index='barrio_localizacion',
    columns='tema',
    values='n',
    aggfunc='sum',
    fill_value=0
)

tabla_pct = tabla.div(tabla.sum(axis=1), axis=0)

# --------- CLUSTERING (k=4) ---------
k = 4
modelo = KMeans(n_clusters=k, random_state=0)
clusters = modelo.fit_predict(tabla_pct)
tabla_pct['cluster'] = clusters

st.subheader("Distribución de Barrios por Clúster")

tabla_clusters = (
    tabla_pct
    .reset_index()
    .groupby('cluster')['barrio_localizacion']
    .apply(lambda x: ', '.join(sorted(x)))
    .reset_index()
    .rename(columns={'barrio_localizacion': 'barrios'})
    .sort_values('cluster')
)

tabla_clusters['cluster'] = tabla_clusters['cluster'] + 1
st.dataframe(tabla_clusters)

# --------- TEMA MÁS RELEVANTE POR CLÚSTER ---------
st.subheader("🏆 Tema más relevante por clúster")

centroides = pd.DataFrame(modelo.cluster_centers_, columns=tabla.columns)
tema_dominante = centroides.idxmax(axis=1)
valor_dominante = centroides.max(axis=1)

df_tema_dominante = pd.DataFrame({
    'cluster': centroides.index + 1,
    'tema': tema_dominante,
    'proporcion': valor_dominante
})

fig, ax = plt.subplots(figsize=(7, 4))

# Paleta de colores sin seaborn
colors = cm.Set2(np.linspace(0, 1, len(df_tema_dominante)))

bars = ax.bar(
    df_tema_dominante['cluster'],
    df_tema_dominante['proporcion'],
    color=colors
)

for i, bar in enumerate(bars):
    tema = df_tema_dominante.iloc[i]['tema']
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 0.02, tema, ha='center', va='bottom', fontsize=9)

plt.title("Tema más relevante por clúster")
plt.ylabel("Proporción media del tema dominante (%)")
plt.xlabel("Clúster")
ax.set_ylim(0, 1)
yticks = ax.get_yticks()
ax.set_yticklabels([f"{int(y*100)}%" for y in yticks])

st.pyplot(fig)

# --------- MAPA FOLIUM ---------
st.subheader("🗺️ Mapa de clústeres por barrio")

@st.cache_data
def cargar_geojson():
    with open("./app/data/barris-barrios.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

geojson_data = cargar_geojson()

tabla_pct = tabla_pct.reset_index()
tabla_pct['barrio_localizacion'] = tabla_pct['barrio_localizacion'].str.upper().str.strip()
cluster_dict = dict(zip(tabla_pct['barrio_localizacion'], tabla_pct['cluster']))

for feature in geojson_data["features"]:
    barrio = feature["properties"]["nombre"].upper().strip()
    cluster = cluster_dict.get(barrio)
    feature["properties"]["cluster"] = cluster
    feature["properties"]["cluster_display"] = int(cluster) + 1 if cluster is not None else 'N/A'

# Nuevos colores para los clústeres
colors_map = cm.get_cmap("Set1", k)
colors_hex = [mcolors.to_hex(colors_map(i)) for i in range(k)]
colores_clusters = {i: colors_hex[i] for i in range(k)}

def style_function(feature):
    cluster = feature['properties'].get('cluster')
    if cluster is None:
        return {
            'fillColor': '#8c8c8c',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.5
        }
    else:
        return {
            'fillColor': colores_clusters.get(int(cluster), '#8c8c8c'),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }

tooltip = GeoJsonTooltip(
    fields=['nombre', 'cluster_display'],
    aliases=['Barrio:', 'Clúster:'],
    localize=True,
    sticky=False,
    labels=True,
    style="""
        background-color: #F0EFEF;
        border: 1px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """
)

m = folium.Map(location=[39.47, -0.38], zoom_start=12)

GeoJson(
    geojson_data,
    style_function=style_function,
    tooltip=tooltip,
    name='Barrios'
).add_to(m)

st_folium(m, width=900, height=600)
