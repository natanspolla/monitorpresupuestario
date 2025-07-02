
import streamlit as st
import requests
import json
import pandas as pd
import numpy as np
from io import StringIO
import time
import re

# Configuración común
columnas_adicionales = [
    "impacto_presupuestario_anio", "impacto_presupuestario_mes",
    "credito_presupuestado", "credito_vigente", "credito_devengado"
]

columnas_desc = [
    "programa_desc", "actividad_desc", "jurisdiccion_desc", "entidad_desc",
    "finalidad_desc", "funcion_desc", "inciso_desc",
    "principal_desc", "clasificador_economico_8_digitos_desc"
]

base_url = "https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv"
headers = {
    "Authorization": "c3e42974-f2d3-41e0-a800-f1d82fe0fc26",
    "Content-Type": "application/json"
}

# --- UI ---
st.title("Consulta de crédito presupuestario")

columna_filtro = st.selectbox("Seleccioná una columna para filtrar", columnas_desc)
valor_filtro = st.text_input("Ingresá el valor a buscar")

desde_anio, hasta_anio = st.slider("Seleccioná el rango de años", 1995, 2025, (2025, 2025))
desde_mes, hasta_mes = st.slider("Seleccioná el rango de meses", 1, 12, (1, 12))

if st.button("Consultar datos"):
    if valor_filtro.strip() == "":
        st.warning("Por favor ingresá un valor para buscar.")
    else:
        dfs = []
        with st.spinner("Consultando API..."):
            for anio in range(desde_anio, hasta_anio + 1):
                payload = {
                    "title": f"Consulta año {anio}",
                    "ejercicios": [anio],
                    "columns": columnas_adicionales + columnas_desc,
                    "filters": [
                        {
                            "column": columna_filtro,
                            "operator": "like",
                            "value": valor_filtro
                        }
                    ]
                }
                try:
                    response = requests.post(base_url, headers=headers, data=json.dumps(payload))
                    if response.status_code == 200:
                        texto_csv = response.text
                        if len(texto_csv.strip()) > 0:
                            df = pd.read_csv(StringIO(texto_csv), decimal=",")
                            if not df.empty:
                                df = df[(df["impacto_presupuestario_mes"] >= desde_mes) &
                                        (df["impacto_presupuestario_mes"] <= hasta_mes)]
                                if not df.empty:
                                    dfs.append(df)
                    else:
                        st.error(f"Año {anio}: status code {response.status_code}")
                except Exception as e:
                    st.error(f"Error al consultar año {anio}: {e}")
                time.sleep(0.3)

        if len(dfs) > 0:
            df_total = pd.concat(dfs, ignore_index=True)
            st.success(f"Total filas obtenidas: {df_total.shape[0]}")

            # --- ✅ Formateo a '1.234.567,89' con conversión previa segura
            cols_numericas = ["credito_presupuestado", "credito_vigente", "credito_devengado"]
            for col in cols_numericas:
                if col in df_total.columns:
                    df_total[col] = pd.to_numeric(df_total[col], errors='coerce')
                    df_total[col] = df_total[col].apply(lambda x:
                        f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if pd.notnull(x) else "")

            st.dataframe(df_total)

            # Exporta Excel con datos numéricos sin el formateo
            nombre_archivo = f"{re.sub(r'[^A-Za-z0-9_]', '_', valor_filtro)}_{desde_anio}_{hasta_anio}.xlsx"
            df_export = pd.concat(dfs, ignore_index=True)
            df_export.to_excel(nombre_archivo, index=False)

            with open(nombre_archivo, "rb") as f:
                st.download_button(
                    label="Descargar Excel (valores numéricos)",
                    data=f,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No se obtuvieron datos para los filtros indicados.")
