import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
import json

# Configuración de página
st.set_page_config(page_title="Asado Pro Calc v2.3 (Cloud)", layout="wide")

# --- CONEXIÓN A SUPABASE ---
# Estos datos se deben cargar preferentemente desde st.secrets por seguridad
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- CAPA DE DATOS (LECTURA) ---
@st.cache_data
def cargar_productos():
    response = supabase.table("productos").select("*").execute()
    return pd.DataFrame(response.data)

def obtener_historial():
    response = supabase.table("historial").select("*").order("fecha", desc=True).execute()
    return pd.DataFrame(response.data)

# --- LÓGICA DE ICONOS ---
def obtener_icono(nombre, df):
    try:
        row = df[df['nombre'] == nombre].iloc[0]
        cat = row['categoria']
        if cat in ['VACUNO', 'CERDO', 'POLLO']: return "🦴" if row['tiene_hueso'] == 1 else "🥩"
        if cat == 'ACHURA': return "🍖"
        if cat == 'BEBIDA':
            n = nombre.lower()
            if "hielo" in n: return "🧊"
            return "🍷" if any(x in n for x in ["vino", "fernet", "cerveza"]) else "🥤"
    except: return "📦"
    return "📦"

df_p = cargar_productos()

# --- NAVEGACIÓN ---
tab_calc, tab_hist = st.tabs(["🔥 Calculadora", "📜 Historial de Asados"])

with tab_calc:
    st.title("🔥 Asado Pro Calc v2.3")
    
    # Sidebar
    st.sidebar.header("⚙️ Ajustes")
    g_h = st.sidebar.slider("Gramos Hombre", 300, 800, 500)
    g_m = st.sidebar.slider("Gramos Mujer", 200, 600, 400)
    g_n = st.sidebar.slider("Gramos Niño", 100, 400, 250)
    f_h = st.sidebar.slider("% Hueso", 0, 50, 25) / 100

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👥 Comensales")
        h = st.number_input("Hombres", 0, 100, 2)
        m = st.number_input("Mujeres", 0, 100, 2)
        n = st.number_input("Niños", 0, 100, 0)
        adultos, total_p = h + m, h + m + n
    with c2:
        def fmt(n): return f"{n} {obtener_icono(n, df_p)}"
        v_s = st.multiselect("Vacuno", df_p[df_p.categoria=='VACUNO'].nombre.tolist(), format_func=fmt)
        c_s = st.multiselect("Cerdo", df_p[df_p.categoria=='CERDO'].nombre.tolist(), format_func=fmt)
        p_s = st.multiselect("Pollo", df_p[df_p.categoria=='POLLO'].nombre.tolist(), format_func=fmt)
        a_s = st.multiselect("Achuras", df_p[df_p.categoria=='ACHURA'].nombre.tolist(), format_func=fmt)
        b_s = st.multiselect("Bebidas", df_p[df_p.categoria=='BEBIDA'].nombre.tolist(), format_func=fmt)

    if st.button("🚀 GENERAR REPORTE"):
        items_c = v_s + c_s + p_s
        if not (items_c or a_s or b_s):
            st.warning("Seleccioná productos.")
        else:
            gr_netos = (h * g_h) + (m * g_m) + (n * g_n)
            lista_f = []
            t_kg = 0
            
            if items_c:
                gr_i = gr_netos / len(items_c)
                for nom in items_c:
                    row = df_p[df_p.nombre == nom].iloc[0]
                    peso = (gr_i/1000) * ((1+f_h) if row.tiene_hueso else 1)
                    t_kg += peso
                    lista_f.append(f"- **{nom} {obtener_icono(nom, df_p)}:** {peso:.2f} kg")
            
            for ach in a_s: lista_f.append(f"- **{ach} 🍖:** {total_p} unidades")
            for beb in b_s:
                ico = obtener_icono(beb, df_p)
                if ico == "🧊": cant = f"{total_p} kg"
                elif ico == "🍷": cant = f"{math.ceil(adultos/(12 if 'Fernet' in beb else 2.5))} botellas"
                else: cant = f"{total_p*1.25:.1f} L"
                lista_f.append(f"- **{beb} {ico}:** {cant}")

            st.session_state['reporte'] = {'detalle': lista_f, 'total_kg': t_kg, 'params': (h, m, n)}

    if 'reporte' in st.session_state:
        rep = st.session_state['reporte']
        st.markdown("---")
        r1, r2 = st.columns(2)
        with r1:
            st.write("### 🛒 Lista de Compra")
            for line in rep['detalle']: st.write(line)
        with r2:
            st.metric("Total Carne", f"{rep['total_kg']:.2f} kg")
            st.subheader("💾 Guardar Asado")
            nombre_e = st.text_input("Nombre del evento:")
            if st.button("Confirmar Guardado en la Nube"):
                if nombre_e:
                    h_s, m_s, n_s = rep['params']
                    data_insert = {
                        "nombre_evento": nombre_e,
                        "hombres": h_s,
                        "mujeres": m_s,
                        "ninos": n_s,
                        "detalle_json": rep['detalle'], # Supabase maneja JSON directo
                        "total_kg": rep['total_kg']
                    }
                    supabase.table("historial").insert(data_insert).execute()
                    st.success(f"✅ '{nombre_e}' guardado permanentemente en Supabase.")
                    st.cache_data.clear() # Limpiamos caché para ver el nuevo registro
                else:
                    st.error("Falta el nombre.")

with tab_hist:
    st.header("📜 Historial en Supabase")
    hist = obtener_historial()
    if hist.empty:
        st.info("No hay asados guardados.")
    else:
        for _, row in hist.iterrows():
            with st.expander(f"📅 {row['fecha'][:10]} | {row['nombre_evento']}"):
                st.write(f"**Comensales:** {row['hombres']}H / {row['mujeres']}M / {row['ninos']}N")
                for d in row['detalle_json']: st.write(d)
                if st.button("Eliminar", key=f"del_{row['id']}"):
                    supabase.table("historial").delete().eq("id", row['id']).execute()
                    st.cache_data.clear()
                    st.rerun()
