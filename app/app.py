from datetime import date, datetime
import os
import json
import urllib.parse
import requests
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN GENERAL Y ESTILOS CSS (ESTILO TIENDA CON CARTILLAS Y MODALES)
# ==============================================================================
st.set_page_config(
    page_title="Salsoteca Carlos Alberto - Guayaquil",
    page_icon="🎷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("""
<style>
    /* Estilos Generales Estilo Tienda / Salsoteca */
    .stApp {
        background-color: #0b0c10;
        color: #ffffff;
        font-family: 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Navbar Fija */
    .navbar-container {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: rgba(15, 16, 26, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 2px solid #d4af37;
        padding: 10px 40px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .navbar-logo {
        font-size: 22px;
        font-weight: 900;
        color: #d4af37;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Banner Slider Hero */
    .hero-slider {
        margin-top: 60px;
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(212, 175, 55, 0.3);
        box-shadow: 0 12px 30px rgba(0,0,0,0.8);
    }
    
    /* Cartillas de Productos / Eventos (Grid 3 por fila) */
    .event-card {
        background: #121420;
        border: 1px solid rgba(212, 175, 55, 0.25);
        border-radius: 14px;
        padding: 16px;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 20px;
    }
    
    .event-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(212, 175, 55, 0.4);
        border-color: #d4af37;
    }
    
    .event-card img {
        width: 100%;
        height: 240px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 12px;
    }
    
    .event-title {
        font-size: 18px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 6px;
    }
    
    .event-badge {
        background: linear-gradient(135deg, #d4af37 0%, #aa7c11 100%);
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 10px;
    }
    
    /* Botones de Acción Estilo Tienda */
    div.stButton > button {
        background: linear-gradient(135deg, #d4af37 0%, #996515 100%) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        width: 100% !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    div.stButton > button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.6) !important;
    }
    
    /* Pie de página */
    .footer-container {
        background: #090a10;
        border-top: 1px solid rgba(212, 175, 55, 0.2);
        padding: 40px 20px;
        margin-top: 50px;
        text-align: center;
        color: #a0a0a0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# HEADER & BARRA DE NAVEGACIÓN FIJA
# ==============================================================================
col_nav1, col_nav2 = st.columns([1, 2])
with col_nav1:
    st.markdown('<div class="navbar-logo">🎷 SALSOTECA CARLOS ALBERTO</div>', unsafe_allow_html=True)

with col_nav2:
    opciones_menu = ["🏠 Inicio", "🎟️ Reservaciones", "📜 Historia", "🛒 Mi Carrito / Pases"]
    menu_sel = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")

st.markdown("<hr style='border-color: rgba(212, 175, 55, 0.3); margin-top: 5px; margin-bottom: 25px;'>", unsafe_allow_html=True)

# ==============================================================================
# SECCIÓN 1: SLIDER DE PRESENTACIÓN AUTOMÁTICO (4 FOTOS)
# ==============================================================================
if menu_sel == "🏠 Inicio":
    st.markdown("### 🌟 Bienvenidos a la Cuna de la Salsa en Guayaquil")
    
    # 4 Fotos de carrusel/slider dinámico
    fotos_slider = [
        {"url": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=1200&q=80", "titulo": "Noches Legendarias de Salsa Live"},
        {"url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80", "titulo": "Las Mejores Orquestas Nacionales e Internacionales"},
        {"url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80", "titulo": "Ambiente VIP y Coctelería de Clase Mundial"},
        {"url": "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?auto=format&fit=crop&w=1200&q=80", "titulo": "Reserva tu Mesa Exclusiva y Siente el Rimo"}
    ]
    
    if "slider_index" not in st.session_state:
        st.session_state.slider_index = 0
        
    foto_actual = fotos_slider[st.session_state.slider_index]
    
    col_s1, col_s2, col_s3 = st.columns([1, 10, 1])
    with col_s1:
        if st.button("❮", key="prev_slide"):
            st.session_state.slider_index = (st.session_state.slider_index - 1) % len(fotos_slider)
            st.rerun()
    with col_s2:
        st.image(foto_actual["url"], caption=foto_actual["titulo"], use_container_width=True)
    with col_s3:
        if st.button("❯", key="next_slide"):
            st.session_state.slider_index = (st.session_state.slider_index + 1) % len(fotos_slider)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================================================================
    # SECCIÓN 2: HISTORIA (EVENTOS PASADOS DE LA ÚLTIMA SEMANA)
    # ==============================================================================
    st.markdown("### 📜 Historia - Los Reventones de la Última Semana")
    col_h1, col_h2, col_h3 = st.columns(3)
    
    historicos = [
        {"titulo": "Tributo a Grupo Niche", "fecha": "Viernes Pasado", "foto": "https://images.unsplash.com/photo-1429962714451-bb934ecdc4ec?auto=format&fit=crop&w=600&q=80"},
        {"titulo": "Noche Guayaca de Maelo Ruiz", "fecha": "Sábado Pasado", "foto": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?auto=format&fit=crop&w=600&q=80"},
        {"titulo": "Mano a Mano Orquestas", "fecha": "Domingo de Gladys", "foto": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=600&q=80"}
    ]
    
    for idx, col in enumerate([col_h1, col_h2, col_h3]):
        with col:
            item = historicos[idx]
            st.image(item["foto"], use_container_width=True)
            st.markdown(f"**{item['titulo']}**")
            st.caption(f"🗓️ {item['fecha']} — ¡Lleno Total!")

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================================================================
    # SECCIÓN 3: EVENTOS ACTIVOS DE LA SEMANA (GRIDA 3 POR FILA ESTILO TIENDA)
    # ==============================================================================
    st.markdown("### 🎷 Cartelera Oficial de la Semana (Eventos Activos)")
    
    # Consulta a API backend
    eventos_activos = []
    try:
        res = requests.get(f"{API_URL}/reservas/eventos/?local_id=1")
        if res.status_code == 200:
            eventos_activos = res.json()
    except Exception:
        eventos_activos = []

    if not eventos_activos:
        # Fallback visual demo si la API local no devuelve datos
        eventos_activos = [
            {"id": 101, "nombre_evento": "Viernes de Azúcar & Salsa", "artista_orquesta": "Orquesta Sabor Son", "fecha_hora": "2026-11-13T21:00:00", "descripcion": "Gran noche bailable con los mejores exponentes de la salsa brava."},
            {"id": 102, "nombre_evento": "Sábado de Gala Salsera", "artista_orquesta": "Invitado Internacional", "fecha_hora": "2026-11-14T21:00:00", "descripcion": "El concierto salsero más esperado del mes en el corazón de Guayaquil."},
            {"id": 103, "nombre_evento": "Domingo de Matinée & Gladys", "artista_orquesta": "DJ Carlos Alberto", "fecha_hora": "2026-11-15T18:00:00", "descripcion": "Tarde de salsa romántica, piqueos y la mejor atención."}
        ]

    # Renderizado en Filas de 3 Columnas
    cols_ev = st.columns(3)
    for i, ev in enumerate(eventos_activos):
        with cols_ev[i % 3]:
            st.markdown(f"""
            <div class="event-card">
                <span class="event-badge">ACTIVO ESTA SEMANA</span>
                <div class="event-title">{ev.get('nombre_evento')}</div>
                <p style="color: #d4af37; font-weight: bold; font-size: 13px;">🎤 {ev.get('artista_orquesta', 'Varios Artistas')}</p>
                <p style="color: #aaaaaa; font-size: 12px;">📅 {ev.get('fecha_hora', '').replace('T', ' ')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Modal / Botón de Acción Estilo Tienda
            if st.button(f"🎟️ Reservar / Ver Pases #{ev.get('id')}", key=f"btn_res_{ev.get('id')}"):
                st.session_state.evento_modal_id = ev.get('id')
                st.session_state.evento_modal_data = ev
                st.rerun()

    # ==============================================================================
    # MODAL DE DETALLE DE CARTILLA
    # ==============================================================================
    if "evento_modal_id" in st.session_state and st.session_state.evento_modal_id:
        ev_m = st.session_state.evento_modal_data
        st.markdown("<hr>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"## 🎫 Detalle de Pase: {ev_m.get('nombre_evento')}")
            st.write(ev_m.get('descripcion', 'Gran show salsero en vivo.'))
            
            with st.form(f"form_compra_pase_{ev_m.get('id')}"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    nombre_cliente = st.text_input("Nombre Completo:")
                    celular_cliente = st.text_input("WhatsApp de Contacto:")
                with col_m2:
                    pases_cant = st.number_input("Número de Pases / Entradas:", min_value=1, max_value=20, value=2)
                    celebracion = st.selectbox("Celebración:", ["Ninguna", "Cumpleaños", "Aniversario", "Reunión de Amigos"])
                
                comprobante_file = st.file_uploader("Adjuntar Comprobante de Pago (Transferencia / Depósito):", type=["jpg", "png", "pdf"])
                
                sub_envio = st.form_submit_button("🚀 Procesar Reserva (Estatus: Por Aprobar)")
                if sub_envio:
                    if not nombre_cliente or not celular_cliente or not comprobante_file:
                        st.error("Por favor completa tus datos y sube tu comprobante de pago.")
                    else:
                        st.success("🎉 ¡Tu reserva fue enviada exitosamente con estatus 'POR APROBAR'! El administrador validará tu pago y te enviará los pases QR a tu WhatsApp.")
                        del st.session_state.evento_modal_id
                        st.balloons()

            if st.button("❌ Cerrar Modal"):
                del st.session_state.evento_modal_id
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================================================================
    # SECCIÓN 4: PUBLICIDAD Y ANUNCIOS AUSPICIANTES
    # ==============================================================================
    st.markdown("### 📢 Publicidad & Marcas Auspiciantes")
    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.info("🍸 **Promo Coctelería 2x1:** Disfruta de nuestros mambos y mojitazos salseros antes de las 10:00 PM.")
        with col_p2:
            st.success("🚗 **Parqueadero Privado Custodiado:** Seguridad garantizada toda la noche para tus vehículos.")

    # ==============================================================================
    # SECCIÓN 5: PIE DE PÁGINA (FOOTER INSTITUCIONAL GUAYAQUIL)
    # ==============================================================================
    st.markdown("""
    <div class="footer-container">
        <h4 style="color: #d4af37;">SALSOTECA CARLOS ALBERTO</h4>
        <p>📍 Guayaquil, Ecuador — La Casa de los Verdaderos Salseros</p>
        <p>📞 Reservas & WhatsApp: +593 99 999 9999 | ✉️ contacto@salsotecacarlosalberto.com</p>
        <p style="font-size: 11px; margin-top: 20px;">© 2026 Salsoteca Carlos Alberto. Todos los derechos reservados. Desarrollado sobre plataforma unificada.</p>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# SUBMENÚ: RESERVACIONES -> CREA TU EVENTO (FIESTA PRIVADA Y PASES)
# ==============================================================================
elif menu_sel == "🎟️ Reservaciones":
    st.title("🎉 Crea tu Propio Evento / Fiesta Privada")
    st.write("Diseña tu celebración en la Salsoteca Carlos Alberto, elige el número de pases y solicita la aprobación del local.")
    
    with st.form("form_crea_tu_evento_privado"):
        st.markdown("### 📝 Datos de la Celebración")
        nombre_fiesta = st.text_input("Nombre de tu Fiesta (Ej: Cumpleaños de Don Carlos)", placeholder="Cumpleaños / Aniversario / Reserva de Grupo")
        fecha_fiesta = st.date_input("Fecha Deseada:", min_value=date.today())
        num_invitados = st.number_input("Cantidad de Pases / Asistentes Estimados:", min_value=5, max_value=200, value=15)
        
        st.markdown("### 💳 Comprobante de Abono / Reserva")
        comprobante_privado = st.file_uploader("Sube el comprobante de pago de reserva:", type=["jpg", "png", "pdf"])
        
        btn_privado = st.form_submit_button("🚀 Enviar Fiesta para Aprobar")
        if btn_privado:
            if not nombre_fiesta or not comprobante_privado:
                st.error("Ingresa el nombre de la celebración y adjunta el comprobante.")
            else:
                st.success("✨ ¡Tu solicitud de fiesta privada fue creada con estatus 'POR APROBAR'! El Administrador revisará los detalles y te emitirá la confirmación oficial.")

elif menu_sel == "📜 Historia":
    st.title("📜 Nuestra Historia & Galería de Noches Salseras")
    st.write("Revive los mejores conciertos, orquestas y noches inolvidables en Guayaquil.")

elif menu_sel == "🛒 Mi Carrito / Pases":
    st.title("🛒 Carrito de Compras & Pases Pendientes")
    st.info("Aquí puedes revisar el estado de tus pases comprados y solicitudes en estado 'Por Aprobar'.")
