import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
import json

# Configuración de página
st.set_page_config(page_title="Asado Pro Calc v2.4", layout="wide")

# --- CONEXIÓN A SUPABASE ---
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- FUNCIONES DE AUTENTICACIÓN ---
def login_usuario(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res
    except Exception as e:
        st.error(f"Credenciales incorrectas o error de conexión: {e}")
        return None

def logout_usuario():
    supabase.auth.sign_out()
    if "user" in st.session_state:
        del st.session_state["user"]
    st.rerun()

# --- CAPA DE DATOS ---
@st.cache_data
def cargar_productos():
    response = supabase.table("productos").select("*").execute()
    return pd.DataFrame(response.data)

def obtener_historial():
    # Gracias a RLS en Supabase, esta consulta solo traerá los del usuario logueado
    response = supabase.table("historial").select("*").order("fecha", desc=True).execute()
    return pd.DataFrame(response.data)

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

# --- LÓGICA DE ACCESO ---
if "user" not in st.session_state:
    st.title("🔐 Acceso Asado Pro")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Ingresar"):
            res = login_usuario(email, password)
            if res:
                st.session_state["user"] = res.user
                st.rerun()
else:
    # --- APP PRINCIPAL (USUARIO LOGUEADO) ---
    df_p = cargar_productos()
    
    # Botón de cierre en Sidebar
    st.sidebar.write(f"Usuario: **{st.session_state['user'].email}**")
    if st.sidebar.button("Cerrar Sesión"):
        logout_usuario()

    tab_calc, tab_hist = st.tabs(["🔥 Calculadora", "📜 Historial de Asados"])

    with tab_calc:
        st.title("🔥 Asado Pro Calc v2.4")
        
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
            total_p = h + m + n
        with c2:
            st.subheader("🥩 Selección")
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
                    elif ico == "🍷": cant = f"{math.ceil((h+m)/(12 if 'Fernet' in beb else 2.5))} botellas"
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
                if st.button("Confirmar Guardado"):
                    if nombre_e:
                        h_s, m_s, n_s = rep['params']
                        data_insert = {
                            "nombre_evento": nombre_e,
                            "hombres": h_s,
                            "mujeres": m_s,
                            "ninos": n_s,
                            "detalle_json": list(rep['detalle']),
                            "total_kg": rep['total_kg']
                            # "user_id": st.session_state["user"].id  <-- QUITÁ ESTA LÍNEA
                        }
                        supabase.table("historial").insert(data_insert).execute()
                        st.success(f"✅ '{nombre_e}' guardado en tu cuenta.")
                        st.cache_data.clear()
                    else:
                        st.error("Falta el nombre.")

    with tab_hist:
        st.header("📜 Mis Asados Guardados")
        hist = obtener_historial()
        if hist.empty:
            st.info("Aún no tienes asados en tu historial.")
        else:
            for _, row in hist.iterrows():
                with st.expander(f"📅 {row['fecha'][:10]} | {row['nombre_evento']}"):
                    st.write(f"**Comensales:** {row['hombres']}H / {row['mujeres']}M / {row['ninos']}N")
                    for d in row['detalle_json']: st.write(d)
                    if st.button("Eliminar", key=f"del_{row['id']}"):
                        supabase.table("historial").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
