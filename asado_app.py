import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
import urllib.parse

# Configuración de página
st.set_page_config(page_title="Asado Pro Calc v2.9", layout="wide")

def get_supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()

# --- FUNCIONES DE APOYO ---
@st.cache_data
def cargar_productos():
    res = supabase.table("productos").select("*").execute()
    return pd.DataFrame(res.data)

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

# --- GESTIÓN DE ESTADO ---
if "user" not in st.session_state: st.session_state["user"] = None
if "session" not in st.session_state: st.session_state["session"] = None
if "anonimo" not in st.session_state: st.session_state["anonimo"] = False

# --- PANTALLA DE ACCESO ---
if st.session_state["user"] is None and not st.session_state["anonimo"]:
    st.title("🔥 Bienvenido a Asado Pro")
    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("🔐 Usuarios Registrados")
        with st.form("login_form"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Ingresar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state["user"] = res.user
                    st.session_state["session"] = res.session
                    st.rerun()
                except: st.error("Error de credenciales")
    with c_r:
        st.subheader("🚶 Modo Invitado")
        if st.button("Entrar como Invitado"):
            st.session_state["anonimo"] = True
            st.rerun()
    st.stop()

# --- APP PRINCIPAL ---
df_p = cargar_productos()

# Sidebar: Ajustes Técnicos
st.sidebar.header("⚙️ Ajustes Técnicos")
g_h = st.sidebar.slider("Gramos Hombre", 300, 800, 500)
g_m = st.sidebar.slider("Gramos Mujer", 200, 600, 400)
g_n = st.sidebar.slider("Gramos Niño", 100, 400, 250)
f_h = st.sidebar.slider("% Extra Hueso", 0, 50, 25) / 100

st.sidebar.markdown("---")
if st.sidebar.button("🔙 Salir / Cerrar Sesión"):
    st.session_state["user"] = None
    st.session_state["anonimo"] = False
    st.rerun()

tab_calc, tab_hist = st.tabs(["🔥 Calculadora", "📜 Historial"])

with tab_calc:
    st.title("🔥 Asado Pro Calc v2.9")
    
    col_input_l, col_input_r = st.columns([1, 2])
    
    with col_input_l:
        st.subheader("👥 Comensales")
        # Volvemos al control estándar que funciona perfecto en móviles
        h = st.number_input("Hombres", min_value=0, max_value=100, value=0, step=1)
        m = st.number_input("Mujeres", min_value=0, max_value=100, value=0, step=1)
        n = st.number_input("Niños", min_value=0, max_value=100, value=0, step=1)
        total_p = h + m + n

    with col_input_r:
        st.subheader("🥩 Selección")
        def fmt(n): return f"{n} {obtener_icono(n, df_p)}"
        
        v_s = st.multiselect("Vacuno", df_p[df_p.categoria=='VACUNO'].nombre.tolist(), format_func=fmt)
        c_s = st.multiselect("Cerdo", df_p[df_p.categoria=='CERDO'].nombre.tolist(), format_func=fmt)
        p_s = st.multiselect("Pollo", df_p[df_p.categoria=='POLLO'].nombre.tolist(), format_func=fmt)
        a_s = st.multiselect("Achuras", df_p[df_p.categoria=='ACHURA'].nombre.tolist(), format_func=fmt)
        b_s = st.multiselect("Bebidas", df_p[df_p.categoria=='BEBIDA'].nombre.tolist(), format_func=fmt)
        
        st.subheader("🥖 Pan")
        usa_pan = st.checkbox("¿Calcular Pan?")
        if usa_pan:
            tipo_pan = st.radio("Forma de comer:", ["Al Plato", "Sándwich"], horizontal=True)

    if st.button("🚀 GENERAR REPORTE", use_container_width=True):
        if total_p == 0:
            st.warning("Debe haber al menos un comensal.")
        else:
            gr_netos = (h * g_h) + (m * g_m) + (n * g_n)
            items_c = v_s + c_s + p_s
            rep_list = []
            t_kg = 0
            
            if items_c:
                gr_i = gr_netos / len(items_c)
                for nom in items_c:
                    row = df_p[df_p.nombre == nom].iloc[0]
                    peso = (gr_i/1000) * ((1+f_h) if row.tiene_hueso else 1)
                    t_kg += peso
                    rep_list.append(f"🥩 {nom}: {peso:.2f} kg")
            
            for ach in a_s: rep_list.append(f"🍖 {ach}: {total_p} unidades")
            for beb in b_s:
                ico = obtener_icono(beb, df_p)
                if ico == "🧊": cant = f"{total_p} kg"
                elif ico == "🍷": cant = f"{math.ceil((h+m)/2.5)} botellas"
                else: cant = f"{total_p*1.25:.1f} L"
                rep_list.append(f"{ico} {beb}: {cant}")
            
            if usa_pan:
                factor_pan = 0.25 if tipo_pan == "Sándwich" else 0.15
                peso_pan = total_p * factor_pan
                rep_list.append(f"🥖 Pan: {peso_pan:.2f} kg")

            st.session_state['reporte'] = {'detalle': rep_list, 'total_kg': t_kg, 'params': (h,m,n)}

    if 'reporte' in st.session_state:
        rep = st.session_state['reporte']
        st.markdown("---")
        st.subheader("📋 Resultados")
        for l in rep['detalle']: st.write(l)
        
        texto_wa = "🔥 *Reporte Asado Pro*\n" + "\n".join(rep['detalle'])
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wa)}"
        st.markdown(f'<a href="{wa_url}" target="_blank" style="background-color: #25D366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; text-align: center; width: 100%;">📲 Enviar por WhatsApp</a>', unsafe_allow_html=True)

        if st.session_state["user"]:
            st.markdown("---")
            n_ev = st.text_input("Nombre del evento:")
            if st.button("💾 Guardar Asado", use_container_width=True):
                if n_ev:
                    h_s, m_s, n_s = rep['params']
                    data = {"nombre_evento": n_ev, "hombres": h_s, "mujeres": m_s, "ninos": n_s, "detalle_json": rep['detalle'], "total_kg": rep['total_kg'], "user_id": st.session_state["user"].id}
                    supabase.postgrest.auth(st.session_state["session"].access_token)
                    supabase.table("historial").insert(data).execute()
                    st.success("Guardado en historial.")
                    st.cache_data.clear()
                else: st.error("Falta nombre.")

with tab_hist:
    if st.session_state["user"]:
        st.header("📜 Mis Asados Guardados")
        # Forzamos refresco de historial consultando directo
        response = supabase.table("historial").select("*").order("fecha", desc=True).execute()
        hist = pd.DataFrame(response.data)
        if hist.empty:
            st.info("Aún no tienes asados guardados.")
        else:
            for _, row in hist.iterrows():
                with st.expander(f"📅 {row['fecha'][:10]} | {row['nombre_evento']}"):
                    st.write(f"**Comensales:** {row['hombres']}H / {row['mujeres']}M / {row['ninos']}N")
                    for d in row['detalle_json']: st.write(d)
                    if st.button("Eliminar", key=f"del_{row['id']}"):
                        supabase.table("historial").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("Logueate para acceder al historial.")
