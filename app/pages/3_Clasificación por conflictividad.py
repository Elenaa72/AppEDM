##import pandas as pd
#import numpy as np
#import streamlit as st
#from sklearn.ensemble import RandomForestClassifier
#from sklearn.model_selection import train_test_split
#from sklearn.metrics import classification_report, accuracy_score
#import plotly.express as px

# ----------- FUNCIONES -----------

def preparar_datos_conflictividad(df, columnas_tema):
    df_copy = df.copy()
    df_copy['fecha'] = pd.to_datetime(df_copy['fecha_entrada_ayuntamiento'])

    # Pivotar para obtener un conteo por tema por barrio
    tabla_pivot = pd.pivot_table(df_copy[df_copy['tema'].isin(columnas_tema)],
                                  index='barrio_localizacion',
                                  columns='tema',
                                  aggfunc='size',
                                  fill_value=0)

    # Aseguramos que todas las columnas_tema estén en el DataFrame
    for col in columnas_tema:
        if col not in tabla_pivot.columns:
            tabla_pivot[col] = 0

    tabla_pivot = tabla_pivot[columnas_tema]  # ordenamos columnas

    # Calculamos el total de incidencias por barrio
    tabla_pivot['total_incidencias'] = tabla_pivot.sum(axis=1)

    # Asignamos nivel de conflictividad
    tabla_pivot['nivel_conflictividad'] = pd.qcut(tabla_pivot['total_incidencias'], q=3, labels=['Bajo', 'Medio', 'Alto'])

    return tabla_pivot


def entrenar_modelo(df, temas):
    X = df[temas]
    y = df['nivel_conflictividad']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    modelo = RandomForestClassifier(random_state=42)
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    reporte = classification_report(y_test, y_pred, output_dict=True)
    accuracy = accuracy_score(y_test, y_pred)
    importancia = pd.Series(modelo.feature_importances_, index=temas).sort_values(ascending=False)
    return modelo, accuracy, reporte, importancia

# ----------- INTERFAZ STREAMLIT -----------

def mostrar_modelo_conflictividad(df):
    st.title("Modelo de Conflictividad por Barrios")
    


    st.subheader("📘 Información sobre el modelo")

    with st.expander("🧠 ¿Qué tipo de modelo estamos utilizando?"):
        st.markdown("""
        Estamos utilizando un modelo de **clasificación supervisada** llamado **Random Forest** (o Bosque Aleatorio).  
        Este algoritmo combina múltiples **árboles de decisión** que aprenden de distintas partes del conjunto de datos. Cada árbol intenta predecir si un barrio tiene un nivel **bajo**, **medio** o **alto** de conflictividad según los temas de incidencia registrados.

        🔍 ¿Por qué Random Forest?
        - Puede manejar fácilmente muchas variables (temas).
        - Es resistente al sobreajuste (no memoriza datos, generaliza).
        - Funciona muy bien con datos categóricos y relaciones no lineales.

        En lugar de depender de una única regla de decisión, el modelo construye múltiples caminos para tomar una **decisión más robusta y consensuada**.
        """)

    with st.expander("⚙️ ¿Cómo se construye el modelo?"):
        st.markdown("""
        El modelo se construye a partir de los datos históricos de incidencias en Valencia. Las fases son:

        #### 1. **Preprocesamiento de datos**
        - Se limpian campos como barrios y distritos.
        - Se eliminan entradas sin datos válidos.
        - Se convierte la fecha en formato legible para el análisis.

        #### 2. **Agrupación temática por barrio**
        - Se cuenta cuántas incidencias ha tenido cada barrio por tema.
        - Se suman para obtener un total de incidencias por barrio.

        #### 3. **Clasificación por conflictividad**
        - Se dividen los barrios en 3 niveles (`bajo`, `medio`, `alto`) usando `qcut`, que agrupa según cuartiles.
        - De esta forma, la clasificación se adapta a la distribución real de datos.

        #### 4. **Entrenamiento del modelo**
        - El modelo aprende a identificar patrones entre los temas de incidencia y el nivel de conflictividad.
        - Se valida automáticamente para comprobar su precisión.

        🔁 Todo este flujo es dinámico: si eliges nuevos temas, el modelo se reentrena al instante.
        """)

    with st.expander("🎯 ¿Qué hace el modelo y qué devuelve?"):
        st.markdown("""
        Este modelo no sólo clasifica, también permite **interpretar el porqué**. ¿Qué se obtiene?

        - 🔮 **Predicción del nivel de conflictividad** para cada barrio.
        - 📊 **Grado de influencia de cada tema** (¿cuál es más relevante?).
        - 📈 **Evaluación de rendimiento**: cómo de bien acierta el modelo.
        - 🧩 **Visualización personalizada** según los temas seleccionados.

        Gracias a estas salidas, no sólo se sabe **qué barrio es más conflictivo**, sino **por qué**.
        """)

    with st.expander("💡 ¿Por qué unas variables influyen más que otras?"):
        st.markdown("""
        El modelo analiza cada **tema** (como "Limpieza", "Ruido", "Covid-19") para ver **cuánto contribuye a separar correctamente los barrios** según su nivel de conflicto.

        🔎 La **importancia de una variable** se basa en:
        - Cuántas veces se usa esa variable en las divisiones de los árboles.
        - Cuánto mejora la clasificación cuando se usa esa variable.

        🧠 Si, por ejemplo, los barrios más conflictivos suelen tener muchas incidencias sobre "Servicios prestados en vía pública", entonces ese tema se convierte en una **clave para el modelo**.

        Esto permite interpretar los resultados con lógica: **¿Qué temas generan más conflicto en la ciudad?**
        """)

    with st.expander("📊 ¿Qué significan los gráficos y tablas?"):
        st.markdown("""
        - **Niveles de conflictividad**: muestra qué barrios tienen más o menos incidencias.
        - **Precisión del modelo**: porcentaje de aciertos en las predicciones.
        - **Rendimiento por clase**: desglose para cada grupo (`bajo`, `medio`, `alto`):
            - **Precisión**: de los que predije como "Alto", ¿cuántos lo eran realmente?
            - **Recall**: de todos los barrios "Alto", ¿cuántos detecté?
            - **F1-score**: equilibrio entre ambos.
        - **Importancia de variables**: cuánto aporta cada tema en la clasificación.
        - **Top barrios conflictivos**: ranking de los más problemáticos.
        - **Top barrios tranquilos**: los que presentan menos conflictos.
        """)

    st.markdown("---")






    columnas_tema = sorted(df['tema'].dropna().unique())
    df_encoded = pd.get_dummies(df[['barrio_localizacion', 'tema']], columns=['tema'])
    temas_encoded = [col for col in df_encoded.columns if col.startswith('tema_')]

    st.subheader("Selección de temas a considerar")
    temas_usados = st.multiselect("Selecciona los temas a incluir en el modelo:", opciones := sorted(df['tema'].dropna().unique()), default=opciones)

    if not temas_usados:
        st.warning("⚠️ Selecciona al menos un tema.")
        return

    df_filtrado = df[df['tema'].isin(temas_usados)]
    df_prep = preparar_datos_conflictividad(df_filtrado, temas_usados)

    st.subheader("Niveles de conflictividad")
    st.dataframe(df_prep[['total_incidencias', 'nivel_conflictividad']].sort_values('total_incidencias', ascending=False))

    st.subheader("Entrenamiento del modelo")
    modelo, acc, reporte, importancia = entrenar_modelo(df_prep, temas_usados)

    st.markdown(f"**Precisión global del modelo:** `{acc:.2%}`")


    st.subheader("🏙️ Barrios más conflictivos")
    st.dataframe(df_prep[df_prep['nivel_conflictividad'] == 'Alto'].sort_values('total_incidencias', ascending=False).head(10))

    st.subheader("🌿 Barrios menos conflictivos")
    st.dataframe(df_prep[df_prep['nivel_conflictividad'] == 'Bajo'].sort_values('total_incidencias').head(10))




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

# ----------- LLAMADA PRINCIPAL -----------
# IMPORTANTE: asegúrate de haber cargado tu DataFrame con incidencias en una variable `df`

mostrar_modelo_conflictividad(df)

