import streamlit as st

st.set_page_config(page_title="Asado Pro Calc", layout="wide")

st.title("🔥 Asado Pro Calc v1.5")
st.markdown("---")

# 1. PARAMETRIZACIÓN (Sidebar)
st.sidebar.header("⚙️ Configuración de Pesos")
g_hombre = st.sidebar.slider("Gramos por Hombre", 300, 800, 500)
g_mujer = st.sidebar.slider("Gramos por Mujer", 200, 600, 400)
g_nino = st.sidebar.slider("Gramos por Niño", 100, 400, 250)
f_hueso = st.sidebar.slider("% Extra por Hueso", 0, 50, 25) / 100

# 2. DICCIONARIOS DE PRODUCTOS
CORTES_VACUNOS = {
    "Asado de Tira (🦴)": True, "Vacío (🥩)": False, "Entraña (🥩)": False,
    "Matambre (🥩)": False, "Bife de Chorizo (🥩)": False, "Ojo de Bife (🥩)": False,
    "Lomo (🥩)": False, "Peceto (🥩)": False, "Colita de Cuadril (🥩)": False,
    "Asado de Bife (🦴)": True, "Tapa de Asado (🥩)": False, "Asado de Falda (🦴)": True
}

CORTES_CERDO = {
    "Pechito con Manta (🦴)": True, "Carré con Hueso (🦴)": True,
    "Carré Deshuesado (🥩)": False, "Bondiola (🥩)": False,
    "Matambrito de Cerdo (🥩)": False, "Solomillo (🥩)": False
}

CORTES_POLLO = {
    "Pollo Mariposa (🦴)": True,
    "Pechuga (🥩)": False,
    "Muslos (🦴)": True,
    "Patas (🦴)": True,
    "Patamuslo (🦴)": True
}

ACHURAS_LIST = ["Chorizo", "Morcilla", "Chinchulín (porción)", "Molleja (porción)", "Riñón"]

# 3. ENTRADA DE DATOS
col1, col2 = st.columns(2)

with col1:
    st.subheader("👥 Comensales")
    h = st.number_input("Hombres", min_value=0, value=2)
    m = st.number_input("Mujeres", min_value=0, value=2)
    n = st.number_input("Niños", min_value=0, value=0)
    total_personas = h + m + n

with col2:
    st.subheader("🥩 Selección de Productos")
    v_sel = st.multiselect("Vacuno", list(CORTES_VACUNOS.keys()))
    c_sel = st.multiselect("Cerdo", list(CORTES_CERDO.keys()))
    p_sel = st.multiselect("Pollo", list(CORTES_POLLO.keys()))
    a_sel = st.multiselect("Achuras (1 u. c/u x persona)", ACHURAS_LIST)

st.subheader("🔥 Fuego")
combustible = st.radio("Método de cocción:", ["Solo Carbón", "Solo Leña", "Mezcla"], horizontal=True)

# 4. PROCESAMIENTO
if st.button("🚀 GENERAR REPORTE DETALLADO"):
    if not (v_sel or c_sel or p_sel or a_sel):
        st.warning("Seleccioná productos para calcular.")
    else:
        # Sumatoria de ítems de carne para el divisor
        items_carne = v_sel + c_sel + p_sel
        cant_items_carne = len(items_carne)
        
        gramos_netos_carne = (h * g_hombre) + (m * g_mujer) + (n * g_nino)
        
        st.markdown("## 📋 Resultados de la Planificación")
        col_res1, col_res2 = st.columns(2)
        total_kg_carne = 0

        with col_res1:
            st.write("### 🥩 Carnes y Pollo")
            if cant_items_carne > 0:
                gr_por_item = gramos_netos_carne / cant_items_carne
                for item in items_carne:
                    usa_hueso = "(🦴)" in item
                    peso = (gr_por_item / 1000) * (1 + f_hueso) if usa_hueso else (gr_por_item / 1000)
                    total_kg_carne += peso
                    st.write(f"- **{item}:** {peso:.2f} kg")
            else:
                st.write("Sin cortes de carne seleccionados.")

            st.write("### 🌭 Achuras")
            if a_sel:
                for achura in a_sel:
                    st.write(f"- **{achura}:** {total_personas} unidades")
            else:
                st.write("Sin achuras seleccionadas.")

        with col_res2:
            st.write("### ⚙️ Logística de Fuego")
            carbon = total_kg_carne if combustible in ["Solo Carbón", "Mezcla"] else 0
            leña = (total_kg_carne * 2) if combustible in ["Solo Leña", "Mezcla"] else 0
            
            st.metric("Peso Total Carne", f"{total_kg_carne:.2f} kg")
            
            if carbon > 0: 
                st.info(f"⬛ **Carbón (Bolsas/Kg):** {carbon:.1f} kg")
            if leña > 0: 
                # Usamos una fogata si el tronco no se ve bien
                st.info(f"🔥 **Leña (Bolsas/Kg):** {leña:.1f} kg")

        st.success("Cálculo finalizado. Reporte listo para la carnicería.")