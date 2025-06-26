import pandas as pd
import matplotlib.pyplot as plt
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

# Cambiar la numeración para que empiece en 1
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

# Gráfico de barras simple sin seaborn
fig, ax = plt.subplots(figsize=(7, 4))
for i, row in df_tema_dominante.iterrows():
    ax.bar(row['cluster'], row['proporcion'], label=row['tema'])

ax.set_title("Tema más relevante por clúster")
ax.set_ylabel("Proporción media del tema dominante")
ax.set_xlabel("Clúster")
ax.set_ylim(0, 1)
ax.set_xticks(df_tema_dominante['cluster'])
ax.legend(title='Tema')
st.pyplot(fig)

# --------- MAPA FOLIUM ---------

@st.cache_data
@st.cache_data
def cargar_geojson_limpio(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    features_limpias = []
    for feature in data.get("features", []):
        try:
            # Limpiar propiedades para solo valores serializables
            props = feature.get("properties", {})
            props_limpias = {}
            for k, v in props.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    props_limpias[k] = v
                else:
                    props_limpias[k] = str(v)

            feature["properties"] = props_limpias

            # Validar que la feature se puede serializar sin error
            json.dumps(feature)

            features_limpias.append(feature)
        except Exception as e:
            st.warning(f"Feature descartada por error de serialización: {e}")

    data["features"] = features_limpias
    return data





# Convertir barrios de clustering a mayúsculas y limpiar espacios
tabla_pct = tabla_pct.reset_index()
tabla_pct['barrio_localizacion'] = tabla_pct['barrio_localizacion'].str.upper().str.strip()
cluster_dict = dict(zip(tabla_pct['barrio_localizacion'], tabla_pct['cluster']))

# Añadir propiedad cluster a cada feature basado en 'nombre' (también en mayúsculas)
for feature in geojson_data["features"]:
    barrio = feature["properties"].get("nombre", "").upper().strip()
    cluster = cluster_dict.get(barrio)
    feature["properties"]["cluster"] = int(cluster) if cluster is not None else -1
    feature["properties"]["cluster_display"] = int(cluster) + 1 if cluster is not None else 0
colores_clusters = {
    0: '#e41a1c',  # rojo
    1: '#377eb8',  # azul
    2: '#4daf4a',  # verde
    3: '#984ea3'   # morado
}
color_sin_cluster = '#8c8c8c'  # gris

def style_function(feature):
    cluster = feature['properties'].get('cluster')
    if cluster is None or cluster == -1:
        return {
            'fillColor': color_sin_cluster,
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.5
        }
    else:
        return {
            'fillColor': colores_clusters.get(cluster, color_sin_cluster),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }


def style_function(feature):
    cluster = feature['properties'].get('cluster')
    if cluster is None or cluster == -1:
        return {
            'fillColor': color_sin_cluster,
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.5
        }
    else:
        return {
            'fillColor': colores_clusters.get(cluster, color_sin_cluster),
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
