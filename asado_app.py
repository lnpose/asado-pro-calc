import streamlit as st
import pandas as pd
import sqlite3
import math
import json

st.set_page_config(page_title="Asado Pro Calc v2.2", layout="wide")

# --- CAPA DE DATOS (SQLITE) ---
def query_db(query, params=(), commit=False):
    conn = sqlite3.connect('asado_pro.db')
    if commit:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        res = None
    else:
        res = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return res

def obtener_icono(nombre, df):
    try:
        row = df[df['nombre'] == nombre].iloc[0]
        cat = row['categoria']
        if cat in ['VACUNO', 'CERDO', 'POLLO']: return "🦴" if row['tiene_hueso'] == 1 else "🥩"
        if cat == 'ACHURA': return "🍖"
        if cat == 'BEBIDA':
            n = nombre.lower()
            if "hielo" in n: return "🧊"
            return "🍷" if any(x in n for x in ["vino", "fernet", "cerveza", "espumante"]) else "🥤"
    except: return "📦"
    return "📦"

# Carga inicial del catálogo
df_p = query_db("SELECT * FROM productos")

# --- NAVEGACIÓN POR TABS ---
tab_calc, tab_hist = st.tabs(["🔥 Calculadora", "📜 Historial de Asados"])

with tab_calc:
    st.title("🔥 Asado Pro Calc v2.2")
    
    # Sidebar de configuración
    st.sidebar.header("⚙️ Ajustes Técnicos")
    g_h = st.sidebar.slider("Gramos Hombre", 300, 800, 500)
    g_m = st.sidebar.slider("Gramos Mujer", 200, 600, 400)
    g_n = st.sidebar.slider("Gramos Niño", 100, 400, 250)
    f_h = st.sidebar.slider("% Extra Hueso", 0, 50, 25) / 100

    col_in1, col_in2 = st.columns(2)
    with col_in1:
        st.subheader("👥 Comensales")
        h = st.number_input("Hombres", 0, 100, 2)
        m = st.number_input("Mujeres", 0, 100, 2)
        n = st.number_input("Niños", 0, 100, 0)
        adultos, total_p = h + m, h + m + n
    
    with col_in2:
        st.subheader("🥩 Selección")
        def fmt(n): return f"{n} {obtener_icono(n, df_p)}"
        v_s = st.multiselect("Vacuno", df_p[df_p.categoria=='VACUNO'].nombre.tolist(), format_func=fmt)
        c_s = st.multiselect("Cerdo", df_p[df_p.categoria=='CERDO'].nombre.tolist(), format_func=fmt)
        p_s = st.multiselect("Pollo", df_p[df_p.categoria=='POLLO'].nombre.tolist(), format_func=fmt)
        a_s = st.multiselect("Achuras", df_p[df_p.categoria=='ACHURA'].nombre.tolist(), format_func=fmt)
        b_s = st.multiselect("Bebidas", df_p[df_p.categoria=='BEBIDA'].nombre.tolist(), format_func=fmt)

    # Lógica de cálculo al presionar el botón
    if st.button("🚀 GENERAR REPORTE"):
        items_c = v_s + c_s + p_s
        if not (items_c or a_s or b_s):
            st.warning("Seleccioná productos.")
        else:
            # Procesamiento de datos
            gr_netos = (h * g_h) + (m * g_m) + (n * g_n)
            lista_final = []
            t_kg = 0
            
            if items_c:
                gr_i = gr_netos / len(items_c)
                for nom in items_c:
                    row = df_p[df_p.nombre == nom].iloc[0]
                    peso = (gr_i/1000) * ((1+f_h) if row.tiene_hueso else 1)
                    t_kg += peso
                    lista_final.append(f"- **{nom} {obtener_icono(nom, df_p)}:** {peso:.2f} kg")
            
            for ach in a_s: lista_final.append(f"- **{ach} 🍖:** {total_p} unidades")
            for beb in b_s:
                ico = obtener_icono(beb, df_p)
                if ico == "🧊": cant = f"{total_p} kg"
                elif ico == "🍷": cant = f"{math.ceil(adultos/(12 if 'Fernet' in beb else 2.5))} botellas"
                else: cant = f"{total_p*1.25:.1f} L"
                lista_final.append(f"- **{beb} {ico}:** {cant}")

            # GUARDADO EN MEMORIA DE SESIÓN
            st.session_state['reporte_activo'] = {
                'detalle': lista_final,
                'total_kg': t_kg,
                'params': (h, m, n)
            }

    # MOSTRAR REPORTE SI EXISTE EN SESIÓN
    if 'reporte_activo' in st.session_state:
        rep = st.session_state['reporte_activo']
        st.markdown("---")
        r1, r2 = st.columns(2)
        with r1:
            st.write("### 🛒 Lista de Compra")
            for line in rep['detalle']: st.write(line)
        with r2:
            st.metric("Total Carne Estimado", f"{rep['total_kg']:.2f} kg")
            
            # --- FORMULARIO DE GUARDADO ---
            st.subheader("💾 Guardar en Historial")
            nombre_e = st.text_input("Nombre del evento:", placeholder="Ej: Asado con los pibes")
            if st.button("Confirmar Guardado"):
                if nombre_e:
                    h_s, m_s, n_s = rep['params']
                    query_db(
                        "INSERT INTO historial (nombre_evento, hombres, mujeres, ninos, detalle_json, total_kg) VALUES (?,?,?,?,?,?)",
                        (nombre_e, h_s, m_s, n_s, json.dumps(rep['detalle']), rep['total_kg']),
                        commit=True
                    )
                    st.success(f"✅ Evento '{nombre_e}' guardado localmente.")
                    # Opcional: limpiar sesión después de guardar
                    # del st.session_state['reporte_activo']
                else:
                    st.error("⚠️ Falta el nombre del evento.")

with tab_hist:
    st.header("📜 Historial Registrado")
    historial = query_db("SELECT * FROM historial ORDER BY fecha DESC")
    
    if historial.empty:
        st.info("No hay asados en la base de datos.")
    else:
        for _, row in historial.iterrows():
            with st.expander(f"📅 {row['fecha']} | {row['nombre_evento']}"):
                st.write(f"**Comensales:** {row['hombres']}H / {row['mujeres']}M / {row['ninos']}N")
                st.write(f"**Carne total:** {row['total_kg']:.2f} kg")
                st.write("**Detalle:**")
                detalles = json.loads(row['detalle_json'])
                for d in detalles: st.write(d)
                
                if st.button("Eliminar Registro", key=f"del_{row['id']}"):
                    query_db("DELETE FROM historial WHERE id = ?", (int(row['id']),), commit=True)
                    st.rerun()