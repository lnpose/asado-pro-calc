import streamlit as st
import math

st.set_page_config(page_title="Asado Pro Calc", layout="wide")

st.title("🔥 Asado Pro Calc v1.6")
st.markdown("---")

# 1. PARAMETRIZACIÓN (Sidebar)
st.sidebar.header("⚙️ Configuración")
g_hombre = st.sidebar.slider("Gramos Carne p/ Hombre", 300, 800, 500)
g_mujer = st.sidebar.slider("Gramos Carne p/ Mujer", 200, 600, 400)
g_nino = st.sidebar.slider("Gramos Carne p/ Niño", 100, 400, 250)
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
    "Pollo Mariposa (🦴)": True, "Pechuga (🥩)": False, "Muslos (🦴)": True,
    "Patas (🦴)": True, "Patamuslo (🦴)": True
}
ACHURAS_LIST = ["Chorizo", "Morcilla", "Chinchulín (porción)", "Molleja (porción)", "Riñón"]

# 3. ENTRADA DE DATOS
col1, col2 = st.columns(2)

with col1:
    st.subheader("👥 Comensales")
    h = st.number_input("Hombres", min_value=0, value=2)
    m = st.number_input("Mujeres", min_value=0, value=2)
    n = st.number_input("Niños", min_value=0, value=0)
    adultos = h + m
    total_personas = adultos + n

with col2:
    st.subheader("🥩 Selección de Comida")
    v_sel = st.multiselect("Vacuno", list(CORTES_VACUNOS.keys()))
    c_sel = st.multiselect("Cerdo", list(CORTES_CERDO.keys()))
    p_sel = st.multiselect("Pollo", list(CORTES_POLLO.keys()))
    a_sel = st.multiselect("Achuras", ACHURAS_LIST)

st.divider()
col3, col4 = st.columns(2)

with col3:
    st.subheader("🥤 Selección de Bebidas")
    b_sel = st.multiselect("Bebidas", [
        "Bebidas sin alcohol (Agua/Gaseosa)", 
        "Vino (Tinto/Blanco)", 
        "Cerveza", 
        "Espumante/Champagne", 
        "Fernet/Destilados", 
        "Hielo"
    ])

with col4:
    st.subheader("🔥 Fuego")
    combustible = st.radio("Método:", ["Solo Carbón", "Solo Leña", "Mezcla"], horizontal=True)

# 4. PROCESAMIENTO
if st.button("🚀 GENERAR REPORTE DETALLADO"):
    if not (v_sel or c_sel or p_sel or a_sel or b_sel):
        st.warning("Seleccioná productos para calcular.")
    else:
        # Cálculo Carnes
        items_carne = v_sel + c_sel + p_sel
        cant_items_carne = len(items_carne)
        gramos_netos_carne = (h * g_hombre) + (m * g_mujer) + (n * g_nino)
        
        st.markdown("## 📋 Reporte de Compra Final")
        res_col1, res_col2 = st.columns(2)
        total_kg_carne = 0

        with res_col1:
            st.write("### 🥩 Carnes y Achuras")
            if cant_items_carne > 0:
                gr_por_item = gramos_netos_carne / cant_items_carne
                for item in items_carne:
                    usa_hueso = "(🦴)" in item
                    peso = (gr_por_item / 1000) * (1 + f_hueso) if usa_hueso else (gr_por_item / 1000)
                    total_kg_carne += peso
                    st.write(f"- **{item}:** {peso:.2f} kg")
            
            if a_sel:
                for achura in a_sel:
                    st.write(f"- **{achura}:** {total_personas} unidades")

            st.write("### ⚙️ Logística de Fuego")
            carbon = total_kg_carne if combustible in ["Solo Carbón", "Mezcla"] else 0
            leña = (total_kg_carne * 2) if combustible in ["Solo Leña", "Mezcla"] else 0
            if carbon > 0: st.info(f"⬛ **Carbón:** {carbon:.1f} kg")
            if leña > 0: st.info(f"🔥 **Leña:** {leña:.1f} kg")

        with res_col2:
            st.write("### 🍾 Bebidas e Insumos")
            if b_sel:
                for bebida in b_sel:
                    if "sin alcohol" in bebida:
                        st.write(f"- **Sin Alcohol:** {total_personas * 1.25:.1f} L (aprox. 1.25L c/u)")
                    elif "Vino" in bebida:
                        st.write(f"- **Vino:** {math.ceil(adultos / 2.5)} botellas (1 c/ 2.5 adultos)")
                    elif "Cerveza" in bebida:
                        st.write(f"- **Cerveza:** {adultos} L (aprox. 3 latas o 2 porrones c/u)")
                    elif "Espumante" in bebida:
                        st.write(f"- **Espumante:** {math.ceil(adultos / 6)} botellas (1 c/ 6 adultos)")
                    elif "Fernet" in bebida:
                        st.write(f"- **Fernet/Destilados:** {math.ceil(adultos / 12)} botellas (1 c/ 12 adultos)")
                    elif "Hielo" in bebida:
                        st.write(f"- **Hielo:** {total_personas} kg (1 kg c/u)")
            else:
                st.write("No se seleccionaron bebidas.")
            
            st.metric("Total Carne", f"{total_kg_carne:.2f} kg")

        st.success("Cálculo procesado. ¡Buen asado!")
