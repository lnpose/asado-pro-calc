import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
import urllib.parse

# Configuración
st.set_page_config(page_title="Asado Pro Calc v2.5", layout="wide")

def get_supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()

# --- FUNCIONES DE APOYO ---
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

@st.cache_data
def cargar_productos():
    res = supabase.table("productos").select("*").execute()
    return pd.DataFrame(res.data)

# --- GESTIÓN DE ESTADO DE SESIÓN ---
if "user" not in st.session_state:
    st.session_state["user"] = None
if "anonimo" not in st.session_state:
    st.session_state["anonimo"] = False

# --- PANTALLA DE ACCESO ---
if st.session_state["user"] is None and not st.session_state["anonimo"]:
    st.title("🔥 Bienvido a Asado Pro")
    
    col_l, col_r = st.columns(2)
    with col_l:
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
                except:
                    st.error("Error de credenciales")
    
    with col_r:
        st.subheader("🚶 Modo Invitado")
        st.write("Calculá tu asado rápido. No podrás guardar historial.")
        if st.button("Entrar como Invitado"):
            st.session_state["anonimo"] = True
            st.rerun()
    st.stop()

# --- APP PRINCIPAL ---
df_p = cargar_productos()

# Sidebar para salir
if st.sidebar.button("🔙 Salir / Cerrar Sesión"):
    st.session_state["user"] = None
    st.session_state["anonimo"] = False
    st.rerun()

tab_calc, tab_hist = st.tabs(["🔥 Calculadora", "📜 Historial"])

with tab_calc:
    st.title("🔥 Asado Pro Calc v2.5")
    
    # 1. COMENSALES CON BOTONES +/-
    st.subheader("👥 Comensales")
    c1, c2, c3 = st.columns(3)
    
    def selector_cant(label, key_name):
        if key_name not in st.session_state: st.session_state[key_name] = 0
        st.write(f"**{label}**")
        sc1, sc2, sc3 = st.columns([1,1,1])
        if sc1.button("➖", key=f"min_{key_name}"): st.session_state[key_name] = max(0, st.session_state[key_name]-1)
        sc2.write(f"### {st.session_state[key_name]}")
        if sc3.button("➕", key=f"add_{key_name}"): st.session_state[key_name] += 1
        return st.session_state[key_name]

    with c1: h = selector_cant("Hombres", "cant_h")
    with c2: m = selector_cant("Mujeres", "cant_m")
    with c3: n = selector_cant("Niños", "cant_n")
    total_p = h + m + n

    st.markdown("---")
    
    # 2. SELECCIÓN
    st.subheader("🥩 Selección")
    def fmt(n): return f"{n} {obtener_icono(n, df_p)}"
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        v_s = st.multiselect("Vacuno", df_p[df_p.categoria=='VACUNO'].nombre.tolist(), format_func=fmt)
        c_s = st.multiselect("Cerdo", df_p[df_p.categoria=='CERDO'].nombre.tolist(), format_func=fmt)
    with col_sel2:
        p_s = st.multiselect("Pollo", df_p[df_p.categoria=='POLLO'].nombre.tolist(), format_func=fmt)
        a_s = st.multiselect("Achuras", df_p[df_p.categoria=='ACHURA'].nombre.tolist(), format_func=fmt)
        b_s = st.multiselect("Bebidas", df_p[df_p.categoria=='BEBIDA'].nombre.tolist(), format_func=fmt)

    # 3. PAN (Lógica solicitada)
    st.subheader("🥖 Pan y Extras")
    usa_pan = st.checkbox("¿Calcular Pan?")
    tipo_pan = "Plato"
    if usa_pan:
        tipo_pan = st.radio("Forma de comer:", ["Al Plato (2 p/p)", "Sándwich (3 p/p)"], horizontal=True)

    if st.button("🚀 GENERAR REPORTE"):
        if total_p == 0:
            st.warning("Agregá comensales primero.")
        else:
            # Lógica de cálculo...
            g_h, g_m, g_n = 500, 400, 250 # Valores base
            gr_netos = (h * g_h) + (m * g_m) + (n * g_n)
            items_c = v_s + c_s + p_s
            
            reporte_list = []
            t_kg = 0
            
            # Carnes
            if items_c:
                gr_i = gr_netos / len(items_c)
                for nom in items_c:
                    row = df_p[df_p.nombre == nom].iloc[0]
                    peso = (gr_i/1000) * (1.25 if row.tiene_hueso else 1)
                    t_kg += peso
                    reporte_list.append(f"🥩 {nom}: {peso:.2f} kg")
            
            # Achuras
            for ach in a_s: reporte_list.append(f"🍖 {ach}: {total_p} uni")
            
            # Bebidas
            for beb in b_s:
                ico = obtener_icono(beb, df_p)
                if ico == "🧊": cant = f"{total_p} kg"
                elif ico == "🍷": cant = f"{math.ceil((h+m)/2.5)} bot"
                else: cant = f"{total_p*1.25:.1f} L"
                reporte_list.append(f"{ico} {beb}: {cant}")
            
            # Pan
            if usa_pan:
                cant_pan = total_p * (3 if "Sándwich" in tipo_pan else 2)
                reporte_list.append(f"🥖 Pan: {cant_pan} unidades")

            st.session_state['reporte'] = {'detalle': reporte_list, 'total_kg': t_kg, 'params': (h,m,n)}

    # MOSTRAR REPORTE
    if 'reporte' in st.session_state:
        rep = st.session_state['reporte']
        st.markdown("---")
        st.subheader("📋 Tu Reporte")
        for line in rep['detalle']: st.write(line)
        
        # BOTÓN WHATSAPP
        texto_wa = "🔥 *Reporte Asado Pro*\n" + "\n".join(rep['detalle'])
        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_wa)}"
        st.markdown(f' <a href="{wa_url}" target="_blank" style="background-color: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">📲 Compartir por WhatsApp</a>', unsafe_allow_html=True)

        # GUARDADO (Solo si no es anónimo)
        if st.session_state["user"]:
            st.markdown("---")
            n_ev = st.text_input("Nombre del evento para el historial:")
            if st.button("💾 Guardar en Nube"):
                if n_ev:
                    h_s, m_s, n_s = rep['params']
                    data = {"nombre_evento": n_ev, "hombres": h_s, "mujeres": m_s, "ninos": n_s, "detalle_json": rep['detalle'], "total_kg": rep['total_kg'], "user_id": st.session_state["user"].id}
                    supabase.postgrest.auth(st.session_state["session"].access_token)
                    supabase.table("historial").insert(data).execute()
                    st.success("Guardado.")
                else: st.error("Falta nombre.")

with tab_hist:
    if st.session_state["user"]:
        # ... (Código de historial igual a v2.4) ...
        st.write("Aquí verás tus asados guardados.")
    else:
        st.info("El historial solo está disponible para usuarios registrados.")
