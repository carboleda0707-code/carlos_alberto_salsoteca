from datetime import date, datetime
import os
import requests
import streamlit as st
from header_global import render_header

def render_agenda_propietario(api_url):
  # Indicar al header global que el portal activo es de propietario
  st.session_state["tipo_portal"] = "propietario"
  
  # Renderizar cabecera limpia y unificada
  render_header(subtitulo="Gestión de Eventos y Reservas")

  # ============================================================
  # RECUPERAR DATOS DE SESIÓN Y LOCALES
  # ============================================================
  user_id = (
      st.session_state.get("propietario_id")
      or st.session_state.get("user_id")
      or st.session_state.get("id")
  )
  
  locales_propietario = []
  local_id_actual = st.session_state.get("local_id_actual")
  eventos = []

  try:
    if user_id:
      res_api = requests.get(f"{api_url}/locales/?propietario_id={user_id}")
      if res_api.status_code == 200:
        data_locales = res_api.json()
        locales_propietario = data_locales if isinstance(data_locales, list) else [data_locales]
  except Exception:
    locales_propietario = []

  # ============================================================
  # MEMBRETE DEL LOCAL (COMPACTO Y ADAPTADO A MÓVIL)
  # ============================================================
  slug_actual = "N/A"
  with st.container(border=True):
    if locales_propietario:
      opciones_locales = {
          f"{loc.get('nombre', loc.get('nombre_local', loc.get('nombre_comercial', 'Local')))} (ID: {loc.get('id')})": loc.get("id")
          for loc in locales_propietario
      }
      nombres_opciones = list(opciones_locales.keys())
      
      if local_id_actual not in opciones_locales.values() and nombres_opciones:
        local_id_actual = opciones_locales[nombres_opciones[0]]
        st.session_state["local_id_actual"] = local_id_actual

      local_seleccionado_nombre = st.selectbox(
          "🏢 Seleccionar Local",
          nombres_opciones,
          index=nombres_opciones.index(next((k for k, v in opciones_locales.items() if v == local_id_actual), nombres_opciones[0])) if nombres_opciones else 0,
          key="selectbox_local_propietario",
          label_visibility="collapsed"
      )
      local_id_actual = opciones_locales[local_seleccionado_nombre]
      st.session_state["local_id_actual"] = local_id_actual

      local_obj = next((loc for loc in locales_propietario if loc.get("id") == local_id_actual), None)

      if local_obj:
        
        col_foto, col_detalles = st.columns([1, 2])
        
        nombre_local = local_obj.get("nombre", local_obj.get("nombre_comercial", "Sin nombre"))
        tipo_local = local_obj.get("tipo_establecimiento", local_obj.get("tipo", "Establecimiento"))
        direccion_local = local_obj.get("direccion", local_obj.get("codigo_ubicacion", "Sin dirección especificada"))
        slug_actual = local_obj.get("slug", "Sin slug")
        imagen_local = local_obj.get("imagen") or local_obj.get("foto")

        with col_foto:
          st.markdown('<div class="local-header-img">', unsafe_allow_html=True)
          imagen_encontrada = None
          if imagen_local:
            for ruta in [
                os.path.join("app", "static", "uploads", imagen_local),
                os.path.join("static", "uploads", imagen_local),
                os.path.join("uploads", imagen_local),
                imagen_local,
            ]:
              if os.path.exists(ruta):
                imagen_encontrada = ruta
                break

          if imagen_encontrada:
            st.image(imagen_encontrada)
          else:
            st.markdown(
                """
                <div style="background: #141625; padding: 10px; text-align: center; border-radius: 6px; border: 1px dashed rgba(255,255,255,0.15); height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <span style="font-size: 18px;">🏢</span>
                    <b style="color: #ffffff; font-size: 9px; margin-top: 4px;">Sin foto</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
          st.markdown('</div>', unsafe_allow_html=True)

        with col_detalles:
          st.markdown(f"<p style='font-size:14px; font-weight:bold; margin-bottom:4px;'>📍 {nombre_local}</p>", unsafe_allow_html=True)
          st.markdown(f"<p style='font-size:11px; margin-bottom:2px;'>🏷️ <b>Tipo:</b> {tipo_local}</p>", unsafe_allow_html=True)
          st.markdown(f"<p style='font-size:11px; margin-bottom:2px;'>🗺️ <b>Dir:</b> {direccion_local}</p>", unsafe_allow_html=True)
          st.markdown(f"<p style='font-size:11px; margin-bottom:0px;'>🔗 <b>Slug:</b> `{slug_actual}`</p>", unsafe_allow_html=True)
    else:
      st.warning("No se encontraron locales asociados.")

  # ============================================================
  # OBTENER EVENTOS DEL LOCAL ACTUAL
  # ============================================================
  try:
    if local_id_actual:
      response = requests.get(f"{api_url}/locales/{local_id_actual}/eventos-propietario")
      if response.status_code == 200:
        eventos = response.json()
  except Exception:
    eventos = []

  # Verificación de Plantilla 'Tu Evento'
  existe_plantilla = any(str(ev.get("estado", "")).strip().lower() == "plantilla" for ev in eventos)
  if not existe_plantilla:
    with st.container(border=True):
      st.subheader("⚡ Plantilla General del Local")
      st.write("Haz clic para crear por primera vez el evento maestro **'Tu Evento'**.")
      if st.button("🚀 Crear / Habilitar 'Tu Evento'"):
        data_plantilla = {
            "local_id": int(local_id_actual or 1),
            "nombre_evento": "Tu Evento",
            "artista_orquesta": "Plantilla General",
            "estado": "plantilla",
            "genero_musical": "General",
            "incluye_piqueos": False,
            "tipo_ambiente": "Principal",
            "capacidad_total": 50,
            "fecha_hora": "2099-12-31T20:00:00",
            "descripcion": "Plantilla oficial para celebraciones y reservas de comensales.",
        }
        try:
          res_crear = requests.post(f"{api_url}/reservas/eventos/", data=data_plantilla)
          if res_crear.status_code in [200, 201]:
            st.success("✨ ¡Plantilla 'Tu Evento' creada con éxito!")
            st.rerun()
          else:
            st.error(f"Error al crear la plantilla: {res_crear.text}")
        except Exception as e:
          st.error(f"Error de conexión: {e}")
  else:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; width: 100%; margin-bottom: 12px;">
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 14, 36, 0.9)); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 6px 12px; color: #34d399; font-size: 11px; display: inline-flex; align-items: center; gap: 6px;">
                <span>✅</span> Plantilla <b>'Tu Evento'</b> activa y disponible.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  # ============================================================
  # SECCIÓN: CREAR NUEVO EVENTO / CARTELERA
  # ============================================================
  with st.expander("➕ Crear Nuevo Evento o Cartelera para la Salsoteca"):
    with st.form("form_crear_nuevo_evento"):
      st.markdown("<p style='font-size:13px; font-weight:bold; color:#00cfff;'>🎉 Registrar un Nuevo Evento</p>", unsafe_allow_html=True)
      
      nuevo_nombre = st.text_input("Nombre del Evento (Ej: Viernes de Salsa Brava)")
      nuevo_artista = st.text_input("Artista u Orquesta Invitada")
      nuevo_genero = st.text_input("Género Musical", value="Salsa / Son")
      
      col_fc_1, col_fc_2 = st.columns(2)
      with col_fc_1:
        nueva_fecha = st.date_input("Fecha del Evento", value=date.today())
      with col_fc_2:
        nueva_hora = st.time_input("Hora de Inicio", value=datetime.strptime("21:00", "%H:%M").time())
        
      nueva_desc = st.text_area("Descripción / Detalles del Evento")
      nuevo_flyer = st.file_uploader("Póster o Flyer del Evento (Imagen)", type=["jpg", "jpeg", "png"])
      
      btn_enviar_evento = st.form_submit_button("🚀 Publicar Evento en Cartelera")
      
      if btn_enviar_evento:
        if not nuevo_nombre:
          st.error("El nombre del evento es obligatorio.")
        else:
          fecha_hora_completa = f"{nueva_fecha}T{nueva_hora.strftime('%H:%M:%S')}"
          data_nuevo = {
              "local_id": int(local_id_actual or 1),
              "nombre_evento": nuevo_nombre,
              "artista_orquesta": nuevo_artista or "Varios Artistas",
              "genero_musical": nuevo_genero,
              "fecha_hora": fecha_hora_completa,
              "descripcion": nueva_desc,
              "estado": "aprobado"
          }
          files_nuevo = {"file": (nuevo_flyer.name, nuevo_flyer.getvalue(), nuevo_flyer.type)} if nuevo_flyer else None

          try:
            res_pub = requests.post(f"{api_url}/reservas/eventos/", data=data_nuevo, files=files_nuevo)
            if res_pub.status_code in [200, 201]:
              st.success("🎉 ¡Evento publicado exitosamente en la cartelera!")
              st.rerun()
            else:
              st.error(f"Error al publicar el evento: {res_pub.text}")
          except Exception as err:
            st.error(f"Error de conexión con el servidor: {err}")

  # Selector de Vista Centrado
  col_cent_1, col_cent_2, col_cent_3 = st.columns([1, 2, 1])
  with col_cent_2:
    vista_seleccionada = st.radio(
        "Seleccionar vista",
        ["🖼️ Cartelera", "📅 Fecha"],
        key="selector_vista_propietario",
        label_visibility="collapsed",
        horizontal=True,
    )

  st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

  # Filtrado por fecha opcional
  fecha_filtro = None
  if vista_seleccionada == "📅 Fecha":
    col_fc1, col_fc2, col_fc3 = st.columns([1, 2, 1])
    with col_fc2:
      with st.container(border=True):
        st.markdown("<p style='text-align:center; font-weight:bold; color:#00cfff; font-size:12px;'>📅 Seleccionar Fecha</p>", unsafe_allow_html=True)
        f_val = st.date_input("Fecha", value=date.today(), key="filtro_fecha_calendario_normal")
        fecha_filtro = f_val.strftime("%Y-%m-%d")

  # Organizar eventos (Plantilla siempre arriba, el resto ordenados por ID desc)
  plantilla_tu_evento = [ev for ev in eventos if ev.get("nombre_evento", "").strip().lower() == "tu evento"]
  otros_eventos = [ev for ev in eventos if ev.get("nombre_evento", "").strip().lower() != "tu evento"]
  otros_eventos = sorted(otros_eventos, key=lambda x: x.get("id", 0), reverse=True)

  if fecha_filtro:
    otros_eventos = [ev for ev in otros_eventos if (ev.get("fecha_hora", "") or "").startswith(fecha_filtro)]

  eventos_a_mostrar = plantilla_tu_evento + otros_eventos

  # ============================================================
  # RENDERIZADO UNIFICADO DE CARTELERA
  # ============================================================
  st.markdown('<div class="cartelera-section">', unsafe_allow_html=True)
  if eventos_a_mostrar:
    num_evs = len(eventos_a_mostrar)
    if num_evs == 1:
      MAX_COLS, elementos_render = 1, eventos_a_mostrar
    elif num_evs == 2:
      MAX_COLS, elementos_render = 2, eventos_a_mostrar
    else:
      MAX_COLS, elementos_render = 2, eventos_a_mostrar

    for i_lote in range(0, len(elementos_render), MAX_COLS):
      lote_actual = elementos_render[i_lote:i_lote + MAX_COLS]
      cols = st.columns(MAX_COLS)

      for j in range(MAX_COLS):
        with cols[j]:
          if j < len(lote_actual) and lote_actual[j] is not None:
            evento = lote_actual[j]
            evento_id = evento.get("id")
            i_global = i_lote + j
            nombre_ev = evento.get("nombre_evento", "Sin nombre")

            with st.container(border=True):
              nombre_imagen = evento.get("imagen")
              imagen_encontrada = None

              if nombre_imagen:
                for ruta in [
                    os.path.join("app", "static", "uploads", nombre_imagen),
                    os.path.join("static", "uploads", nombre_imagen),
                    os.path.join("uploads", nombre_imagen),
                    nombre_imagen,
                ]:
                  if os.path.exists(ruta):
                    imagen_encontrada = ruta
                    break

              if imagen_encontrada:
                st.image(imagen_encontrada, use_container_width=True)
              else:
                st.markdown(
                    """
                    <div style="background: #141625; padding: 12px 4px; text-align: center; border-radius: 6px; border: 1px dashed rgba(255,255,255,0.15); height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                        <span style="font-size: 16px;">🎧</span><br>
                        <b style="color: #ffffff; font-size: 10px;">Tu Evento</b><br>
                        <span style="font-size: 9px; color: #d6d5df;">Sin póster</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

              st.markdown(f"<p class='card-title' title='{nombre_ev}'>{nombre_ev}</p>", unsafe_allow_html=True)

              fecha_raw = evento.get("fecha_hora", "N/A")
              fecha_corta = fecha_raw.split("T")[0] if "T" in fecha_raw else fecha_raw
              artista = evento.get("artista_orquesta", "N/A")

              st.markdown(f"<p class='card-info'>🆔 <b>ID:</b> {evento_id}</p>", unsafe_allow_html=True)
              st.markdown(f"<p class='card-info'>📅 {fecha_corta}</p>", unsafe_allow_html=True)
              st.markdown(f"<p class='card-info' title='{artista}'>🎤 {artista}</p>", unsafe_allow_html=True)

              estado_ev = evento.get("estado", "aprobado")
              if estado_ev == "pendiente":
                st.markdown("<p style='color: #fbbf24; font-size: 10px; margin: 0 0 4px 0; text-align: center;'>⏳ Pendiente</p>", unsafe_allow_html=True)
                if st.button("✅ Aprobar", key=f"aprobar_{evento_id}_{i_global}"):
                  try:
                    res_aprob = requests.put(f"{api_url}/reservas/eventos/{evento_id}/estado", json={"estado": "aprobado"})
                    if res_aprob.status_code in [200, 201]:
                      st.success("¡Aprobado!")
                      st.rerun()
                    else:
                      st.error(f"Error: {res_aprob.text}")
                  except Exception as ex:
                    st.error(f"Error: {ex}")

              if st.button("✏️ Editar", key=f"edit_{evento_id}_{i_global}"):
                st.session_state.editando_evento_id = evento_id
                st.rerun()

              if st.button("🗑️ Borrar", key=f"del_{evento_id}_{i_global}"):
                try:
                  del_response = requests.delete(f"{api_url}/reservas/eventos/{evento_id}")
                  if del_response.status_code == 404:
                    del_response = requests.delete(f"{api_url}/eventos/{evento_id}")

                  if del_response.status_code in [200, 204]:
                    st.success("¡Eliminado!")
                    st.rerun()
                  else:
                    st.error("No se pudo eliminar.")
                except Exception as ex:
                  st.error(f"Error: {ex}")
  else:
    st.info("No hay eventos programados para mostrar.")
  st.markdown('</div>', unsafe_allow_html=True)

  # ============================================================
  # MODAL / FORMULARIO DE EDICIÓN
  # ============================================================
  if "editando_evento_id" in st.session_state and st.session_state.editando_evento_id:
    id_a_editar = st.session_state.editando_evento_id
    evento_actual = next((ev for ev in eventos if int(ev.get("id", 0)) == int(id_a_editar)), None)

    if not evento_actual:
      try:
        res_all = requests.get(f"{api_url}/reservas/eventos/")
        if res_all.status_code == 200:
          evento_actual = next((ev for ev in res_all.json() if int(ev.get("id", 0)) == int(id_a_editar)), None)
      except Exception:
        pass

    st.info(f"✏️ Estás editando el Evento ID: {id_a_editar}")

    if evento_actual:
      with st.form(f"form_editar_evento_{id_a_editar}"):
        n_nombre = st.text_input("Nombre del Evento", value=evento_actual.get("nombre_evento", ""))
        n_artista = st.text_input("Artista u Orquesta", value=evento_actual.get("artista_orquesta", ""))
        n_desc = st.text_area("Descripción", value=evento_actual.get("descripcion", ""))

        f_raw = evento_actual.get("fecha_hora", "")
        try:
          dt_parsed = datetime.fromisoformat(f_raw.replace("Z", ""))
          d_val, t_val = dt_parsed.date(), dt_parsed.time()
        except Exception:
          d_val, t_val = datetime.today().date(), datetime.now().time()

        col_f, col_h = st.columns(2)
        with col_f:
          min_d, max_d = datetime(2024, 1, 1).date(), datetime(2100, 12, 31).date()
          if d_val > max_d:
            d_val = min_d
          n_fecha = st.date_input("Nueva Fecha / Vigencia Plantilla", value=d_val, min_value=min_d, max_value=max_d)
        with col_h:
          n_hora = st.time_input("Nueva Hora", value=t_val)

        n_imagen = st.file_uploader("Actualizar Imagen o Flyer (Opcional)", type=["jpg", "jpeg", "png"])
        btn_guardar = st.form_submit_button("💾 Guardar Cambios")

        if btn_guardar:
          fecha_hora_str = f"{n_fecha}T{n_hora.strftime('%H:%M:%S')}"
          data_act = {
              "nombre_evento": n_nombre,
              "artista_orquesta": n_artista,
              "fecha_hora": fecha_hora_str,
              "descripcion": n_desc,
          }
          files_act = {"file": (n_imagen.name, n_imagen.getvalue(), n_imagen.type)} if n_imagen else None

          try:
            resp_upd = requests.put(f"{api_url}/reservas/eventos/{id_a_editar}", data=data_act, files=files_act)
            if resp_upd.status_code in [200, 201]:
              st.success("¡Evento actualizado con éxito!")
              del st.session_state.editando_evento_id
              st.rerun()
            else:
              st.error(f"Error al actualizar: {resp_upd.text}")
          except Exception as e:
            st.error(f"Error de conexión: {e}")
    else:
      st.error(f"No se pudo cargar la información del evento ID {id_a_editar}.")

    if st.button("❌ Cancelar Edición"):
      del st.session_state.editando_evento_id
      st.rerun()