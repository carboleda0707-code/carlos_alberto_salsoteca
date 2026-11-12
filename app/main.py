import os
import shutil
import re
import uuid
import urllib.parse
import traceback
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine, Base, get_db
from app.models import Local, Evento, UsuarioFinal, Reserva, BannerSlider, Usuario, IngresoPuerta, PlantillaCelebracionBase
from app.config import obtener_tarifas_sistema
from app.r2_storage import upload_file_to_r2

# Crear las tablas en la base de datos si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Salsoteca Carlos Alberto API", version="1.0.0")

# --- INCLUIR ROUTERS ADICIONALES ---
from app.routers import reservas_personalizadas, checkin
app.include_router(reservas_personalizadas.router)
app.include_router(checkin.router)

BASE_DIR = Path(__file__).resolve().parent.parent

# Montar archivos estáticos locales
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Configurar templates de Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Ruta principal: Sirve el frontend (index.html)
@app.get("/")
def read_root(request: Request):
    print("--- [CHIVATO] Petición recibida en la ruta raíz '/' ---")
    index_path = BASE_DIR / "app" / "templates" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Bienvenido a la API de Salsoteca Carlos Alberto."}

# Ruta para el Panel de Administración Web
@app.get("/admin", response_class=HTMLResponse)
def panel_administracion(request: Request):
    print("--- [CHIVATO] Petición recibida en '/admin' (Panel de Administración) ---")
    return templates.TemplateResponse(request, "admin_panel.html")

# ==========================================
# ENDPOINTS: ADMINISTRADORES Y LOCALES / SUCURSALES
# ==========================================
@app.post("/api/admin/propietarios/")
def crear_propietario(
    nombre: str = Form(...),
    telefono: str = Form(None),
    correo: str = Form(...),
    db: Session = Depends(get_db)
):
    nuevo_usuario = Usuario(
        nombre=nombre, 
        correo=correo,
        contrasena="temporal_hash_admin",
        rol="propietario"
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"mensaje": "Propietario/Administrador registrado con éxito", "id": nuevo_usuario.propietario_id}

@app.get("/api/admin/propietarios/")
def listar_propietarios(db: Session = Depends(get_db)):
    return db.query(Usuario).filter(Usuario.rol == "propietario").all()


# ==========================================
# ENDPOINTS: LOGOTIPO DINÁMICO DEL LOCAL (Cloudflare R2)
# ==========================================
@app.post("/api/admin/local/logo")
async def actualizar_logo_local(
    local_id: int = Form(1),
    logo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        file_extension = Path(logo.filename).suffix
        filename_guardado = f"logo_local_{local_id}_{uuid.uuid4().hex[:6]}{file_extension}"
        
        upload_file_to_r2(
            file_obj=logo.file,
            filename=filename_guardado,
            content_type=logo.content_type
        )

        R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-3244093a45bd47d9a30548ef0924bb49.r2.dev").rstrip('/')
        logo_url = f"{R2_PUBLIC_URL}/{filename_guardado}"

        # Buscamos directamente en la tabla 'lugares'
        local = db.query(Local).filter(Local.id == local_id).first()
        if not local:
            local = Local(id=local_id, nombre="Salsoteca Carlos Alberto", logo_url=logo_url)
            db.add(local)
        else:
            local.logo_url = logo_url

        db.commit()
        return {"mensaje": "¡Logotipo actualizado con éxito en la nube!", "logo_url": logo_url}
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al subir el logotipo: {str(e)}")

@app.get("/api/admin/local/info/")
def obtener_info_local(local_id: int = 1, db: Session = Depends(get_db)):
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-3244093a45bd47d9a30548ef0924bb49.r2.dev").rstrip('/')
    local = db.query(Local).filter(Local.id == local_id).first()
    logo_url = ""
    if local and getattr(local, 'logo_url', None):
        logo_url = local.logo_url
        if logo_url and not logo_url.startswith("http"):
            logo_url = f"{R2_PUBLIC_URL}/{logo_url}"
            
    return {
        "id": local.id if local else local_id,
        "nombre": local.nombre if local else "Salsoteca Carlos Alberto",
        "logo_url": logo_url
    }


@app.post("/api/admin/locales/")
def crear_local(
    propietario_id: int = Form(...),
    nombre_local: str = Form(...),
    tipo_establecimiento: str = Form("Salsoteca / Bar"),
    direccion: str = Form(None),
    ciudad: str = Form("Guayaquil"),
    db: Session = Depends(get_db)
):
    try:
        slug_base = re.sub(r'[^a-zA-Z0-9]', '-', nombre_local.lower())
        slug_limpio = re.sub(r'-+', '-', slug_base).strip('-')

        existente = db.query(Local).filter(Local.slug == slug_limpio).first()
        if existente:
            slug_limpio = f"{slug_limpio}-{int(datetime.utcnow().timestamp())}"

        nuevo_local = Local(
            propietario_id=propietario_id,
            nombre=nombre_local,
            tipo_establecimiento=tipo_establecimiento,
            direccion=direccion,
            ciudad=ciudad,
            slug=slug_limpio
        )
        db.add(nuevo_local)
        db.commit()
        db.refresh(nuevo_local)
        return {"mensaje": "Local/Sucursal registrado con éxito", "id": nuevo_local.id, "slug": slug_limpio}

    except SQLAlchemyError as sqle:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error de Base de Datos: {str(sqle.orig)}")
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/admin/locales/")
def listar_locales(db: Session = Depends(get_db)):
    return db.query(Local).all()


# ==========================================
# ENDPOINTS SECCIÓN 1: SLIDER Y BANNERS (Cloudflare R2)
# ==========================================
@app.post("/api/admin/slider/{posicion}")
async def actualizar_banner_slider(
    posicion: int,
    file: UploadFile = File(...),
    duracion_segundos: int = Form(5),
    caption: str = Form(None),
    db: Session = Depends(get_db)
):
    if posicion not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="La posición debe ser un número entre 1 y 4")

    file_extension = Path(file.filename).suffix
    filename_guardado = f"slider_{posicion}_{uuid.uuid4().hex[:6]}{file_extension}"
    
    upload_file_to_r2(
        file_obj=file.file,
        filename=filename_guardado,
        content_type=file.content_type
    )

    R2_PUBLIC_URL = "https://pub-3244093a45bd47d9a30548ef0924bb49.r2.dev"
    imagen_url = f"{R2_PUBLIC_URL}/{filename_guardado}"

    banner = db.query(BannerSlider).filter(BannerSlider.posicion == posicion).first()
    if banner:
        banner.imagen_url = imagen_url
        banner.duracion_segundos = duracion_segundos
        banner.caption = caption
    else:
        banner = BannerSlider(
            posicion=posicion, 
            imagen_url=imagen_url, 
            duracion_segundos=duracion_segundos, 
            caption=caption
        )
        db.add(banner)
    
    db.commit()
    db.refresh(banner)
    return {
        "mensaje": f"Banner #{posicion} actualizado con éxito en R2",
        "posicion": posicion,
        "imagen_url": banner.imagen_url
    }

@app.get("/api/slider/")
def obtener_banners_slider(db: Session = Depends(get_db)):
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-3244093a45bd47d9a30548ef0924bb49.r2.dev").rstrip('/')
    banners = db.query(BannerSlider).order_by(BannerSlider.posicion.asc()).all()
    
    resultado = []
    for b in banners:
        img_url = b.imagen_url or ""
        if img_url and not img_url.startswith("http"):
            img_url = f"{R2_PUBLIC_URL}/{img_url}"
            
        resultado.append({
            "posicion": b.posicion, 
            "imagen_url": img_url, 
            "duracion_segundos": getattr(b, 'duracion_segundos', 5),
            "caption": getattr(b, 'caption', '')
        })
    return resultado


# ==========================================
# ENDPOINTS: PLANTILLA BASE DE CELEBRACIÓN (Cloudflare R2)
# ==========================================
@app.get("/api/admin/plantilla-celebracion/")
def obtener_plantilla_base(db: Session = Depends(get_db)):
    plantilla = db.query(PlantillaCelebracionBase).filter(PlantillaCelebracionBase.local_id == 1).first()
    if not plantilla:
        plantilla = PlantillaCelebracionBase(
            local_id=1,
            titulo_base="Tu Evento - Celebración Especial",
            imagen_base="evento_default.jpg",
            precio_cover_defecto=10.00,
            precio_mesa_defecto=50.00,
            descripcion_base="Personaliza tu festejo con nosotros. Selecciona la fecha y el tipo de celebración."
        )
        db.add(plantilla)
        db.commit()
        db.refresh(plantilla)
    return plantilla


@app.post("/api/admin/plantilla-celebracion/")
async def guardar_plantilla_base(
    local_id: int = Form(1),
    titulo_base: str = Form(...),
    precio_cover_defecto: float = Form(10.00),
    precio_mesa_defecto: float = Form(50.00),
    descripcion_base: str = Form(None),
    file_base: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    plantilla = db.query(PlantillaCelebracionBase).filter(PlantillaCelebracionBase.local_id == local_id).first()
    
    imagen_nombre = plantilla.imagen_base if plantilla else "evento_default.jpg"
    if file_base and file_base.filename:
        file_extension = Path(file_base.filename).suffix
        imagen_nombre = f"plantilla_base_{uuid.uuid4().hex[:6]}{file_extension}"
        
        upload_file_to_r2(
            file_obj=file_base.file,
            filename=imagen_nombre,
            content_type=file_base.content_type
        )

    if not plantilla:
        plantilla = PlantillaCelebracionBase(
            local_id=local_id,
            titulo_base=titulo_base,
            imagen_base=imagen_nombre,
            precio_cover_defecto=precio_cover_defecto,
            precio_mesa_defecto=precio_mesa_defecto,
            descripcion_base=descripcion_base
        )
        db.add(plantilla)
    else:
        plantilla.titulo_base = titulo_base
        plantilla.imagen_base = imagen_nombre
        plantilla.precio_cover_defecto = precio_cover_defecto
        plantilla.precio_mesa_defecto = precio_mesa_defecto
        plantilla.descripcion_base = descripcion_base

    db.commit()
    db.refresh(plantilla)
    return {"mensaje": "Plantilla maestra de celebración actualizada con éxito en R2", "id": plantilla.id}


@app.get("/api/config/tarifas")
def obtener_tarifas_config():
    return obtener_tarifas_sistema()


# ==========================================
# ENDPOINTS DE EVENTOS Y CARTELERA (Cloudflare R2)
# ==========================================
@app.get("/api/reservas/eventos/")
@app.get("/reservas/eventos/")
def listar_eventos(local_id: int = 1, db: Session = Depends(get_db)):
    eventos = db.query(Evento).filter(
        Evento.local_id == local_id,
        Evento.estado != "plantilla_maestra"
    ).all()
    return eventos

@app.post("/api/reservas/eventos/")
@app.post("/reservas/eventos/")
async def crear_evento(
    local_id: int = Form(...),
    nombre_evento: str = Form(...),
    artista_orquesta: str = Form(None),
    fecha_hora: str = Form(...),
    descripcion: str = Form(None),
    estado: str = Form("aprobado"),
    precio_cover: Optional[float] = Form(None),
    precio_mesa: Optional[float] = Form(None),
    descripcion_mesa: Optional[str] = Form(None),
    precio_promocion: Optional[float] = Form(None),
    descripcion_promocion: Optional[str] = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    imagen_nombre = None
    if file and file.filename:
        file_extension = Path(file.filename).suffix
        imagen_nombre = f"evento_{uuid.uuid4().hex[:8]}{file_extension}"
        
        upload_file_to_r2(
            file_obj=file.file,
            filename=imagen_nombre,
            content_type=file.content_type
        )

    try:
        fecha_limpia = fecha_hora.replace('T', ' ')
        if len(fecha_limpia) == 16:
            fecha_limpia += ":00"
        fecha_dt = datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        fecha_dt = datetime.utcnow()

    nuevo_evento = Evento(
        local_id=local_id,
        nombre_evento=nombre_evento,
        artista_orquesta=artista_orquesta,
        fecha_hora=fecha_dt,
        descripcion=descripcion,
        imagen=imagen_nombre,
        estado=estado,
        precio_cover=precio_cover,
        precio_mesa=precio_mesa,
        descripcion_mesa=descripcion_mesa,
        precio_promocion=precio_promocion,
        descripcion_promocion=descripcion_promocion
    )
    
    try:
        db.add(nuevo_evento)
        db.commit()
        db.refresh(nuevo_evento)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error de BD: {str(e)}")

    return {"mensaje": "Evento creado exitosamente con tarifas en R2", "id": nuevo_evento.id}

@app.put("/api/reservas/eventos/{evento_id}")
@app.put("/reservas/eventos/{evento_id}")
async def actualizar_evento(
    evento_id: int,
    nombre_evento: str = Form(None),
    artista_orquesta: str = Form(None),
    fecha_hora: str = Form(None),
    descripcion: str = Form(None),
    precio_cover: Optional[float] = Form(None),
    precio_mesa: Optional[float] = Form(None),
    descripcion_mesa: Optional[str] = Form(None),
    precio_promocion: Optional[float] = Form(None),
    descripcion_promocion: Optional[str] = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if nombre_evento is not None:
        evento.nombre_evento = nombre_evento
    if artista_orquesta is not None:
        evento.artista_orquesta = artista_orquesta
    
    if fecha_hora is not None and fecha_hora != "":
        try:
            fecha_limpia = fecha_hora.replace('T', ' ')
            if len(fecha_limpia) == 16:
                fecha_limpia += ":00"
            evento.fecha_hora = datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    if descripcion is not None:
        evento.descripcion = descripcion

    evento.precio_cover = precio_cover
    evento.precio_mesa = precio_mesa
    evento.descripcion_mesa = descripcion_mesa
    evento.precio_promocion = precio_promocion
    evento.descripcion_promocion = descripcion_promocion

    if file and file.filename:
        file_extension = Path(file.filename).suffix
        imagen_nombre = f"evento_{uuid.uuid4().hex[:8]}{file_extension}"
        
        upload_file_to_r2(
            file_obj=file.file,
            filename=imagen_nombre,
            content_type=file.content_type
        )
        evento.imagen = imagen_nombre

    db.commit()
    db.refresh(evento)
    return {"mensaje": "Evento actualizado correctamente en R2", "id": evento.id}

@app.delete("/api/reservas/eventos/{evento_id}")
@app.delete("/reservas/eventos/{evento_id}")
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(evento)
    db.commit()
    return {"mensaje": "Evento eliminado correctamente"}


# ==========================================
# ENDPOINT DE CHECKOUT UNIFICADO (Cloudflare R2)
# ==========================================
@app.post("/api/checkout/carrito")
async def procesar_checkout_carrito(
    cedula: str = Form(...),
    nombre: str = Form(...),
    telefono: str = Form(...),
    email: Optional[str] = Form(None),
    items_json: str = Form(...),
    comprobante: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        items = json.loads(items_json)
        if not items:
            raise HTTPException(status_code=400, detail="El carrito está vacío.")

        file_extension = Path(comprobante.filename).suffix
        file_name = f"comprobante_{cedula}_{uuid.uuid4().hex[:6]}{file_extension}"
        
        upload_file_to_r2(
            file_obj=comprobante.file,
            filename=file_name,
            content_type=comprobante.content_type
        )

        cliente = db.query(UsuarioFinal).filter(UsuarioFinal.cedula == cedula).first()
        if not cliente:
            cliente = UsuarioFinal(
                cedula=cedula,
                nombre=nombre,
                telefono=telefono,
                email=email or f"{cedula}@salsoteca.ec",
                password_hash="temp_hash_web"
            )
            db.add(cliente)
            db.commit()
            db.refresh(cliente)

        monto_total_global = 0.0
        reservas_creadas = []

        for item in items:
            subtotal_item = float(item.get("subtotal", 0.0))
            monto_total_global += subtotal_item
            
            codigo_aleatorio = f"RES-{int(datetime.utcnow().timestamp())}-{os.urandom(2).hex()}"
            
            nueva_reserva = Reserva(
                evento_id=item.get("evento_id"),
                cliente_id=cliente.id,
                cantidad_personas=item.get("cantidad_covers", item.get("cantidad_personas", 1)),
                cantidad_mesas=item.get("cantidad_mesas", 0),
                monto_total=subtotal_item,
                comprobante_pago=file_name,
                codigo_reserva=codigo_aleatorio,
                estado_reserva="Por Aprobar",
                nombre_personalizado=item.get("nombre_personalizado"),
                fecha_personalizada=item.get("fecha_personalizada"),
                mostrar_en_cartelera=item.get("mostrar_en_cartelera", True)
            )
            db.add(nueva_reserva)
            reservas_creadas.append(nueva_reserva)

        db.commit()

        return {
            "success": True,
            "mensaje": "¡Compra procesada con éxito! Tus reservas se encuentran en estatus 'Por Aprobar'.",
            "total_items": len(items),
            "monto_total": monto_total_global,
            "comprobante": file_name
        }

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el checkout del carrito: {str(e)}")


# ==========================================
# ENDPOINTS DE RESERVAS Y CONTROL EN PUERTA (Cloudflare R2)
# ==========================================
@app.post("/reservas/con_comprobante/")
async def crear_reserva_con_comprobante(
    evento_id: int = Form(...),
    cliente_id: int = Form(1),
    cliente_nombre: str = Form("Cliente Web"),
    cliente_telefono: str = Form("0999999999"),
    cantidad_personas: int = Form(1),
    cantidad_mesas: int = Form(0),
    monto_total: float = Form(0.0),
    tipo_reserva: str = Form("Cover"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_extension = Path(file.filename).suffix
    nombre_limpio = f"comprobante_{uuid.uuid4().hex[:6]}{file_extension}"
    
    upload_file_to_r2(
        file_obj=file.file,
        filename=nombre_limpio,
        content_type=file.content_type
    )

    cliente = db.query(UsuarioFinal).filter(UsuarioFinal.id == cliente_id).first()
    if not cliente:
        cliente = UsuarioFinal(
            id=cliente_id, 
            nombre=cliente_nombre, 
            telefono=cliente_telefono, 
            email=f"cliente_{int(datetime.utcnow().timestamp())}@salsoteca.com",
            password_hash="temp_hash_web"
        )
        db.add(cliente)
        db.commit()

    codigo_aleatorio = f"RES-{int(datetime.utcnow().timestamp())}"

    nueva_reserva = Reserva(
        evento_id=evento_id,
        cliente_id=cliente.id,
        cantidad_personas=cantidad_personas,
        cantidad_mesas=cantidad_mesas,
        monto_total=monto_total,
        tipo_reserva=tipo_reserva,
        comprobante_pago=nombre_limpio,
        codigo_reserva=codigo_aleatorio,
        estado_reserva="Por Aprobar"
    )

    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)

    return {
        "mensaje": "Reserva combinada creada exitosamente con estatus Por Aprobar en R2",
        "reserva_id": nueva_reserva.id,
        "monto_total": float(nueva_reserva.monto_total),
        "estado": nueva_reserva.estado_reserva
    }


@app.get("/api/admin/reservas/")
def listar_reservas_admin(db: Session = Depends(get_db)):
    reservas = db.query(Reserva).all()
    resultado = []
    for r in reservas:
        cliente_nom = r.cliente.nombre if r.cliente else "Cliente Web"
        cliente_tel = r.cliente.telefono if r.cliente else "Sin Teléfono"
        evento_nom = r.evento.nombre_evento if r.evento else (r.nombre_personalizado or "Celebración Personalizada")
        
        resultado.append({
            "id": r.id,
            "codigo": r.codigo_reserva,
            "cliente_nombre": cliente_nom,
            "cliente_telefono": cliente_tel,
            "evento_nombre": evento_nom,
            "cantidad_personas": r.cantidad_personas,
            "cantidad_mesas": r.cantidad_mesas,
            "monto_total": float(r.monto_total or 0.0),
            "comprobante_pago": r.comprobante_pago,
            "estado": r.estado_reserva,
            "mostrar_en_cartelera": getattr(r, 'mostrar_en_cartelera', True)
        })
    return resultado


@app.put("/api/admin/reservas/{reserva_id}/estado")
def actualizar_estado_reserva(
    reserva_id: int, 
    data: dict, 
    db: Session = Depends(get_db)
):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    nuevo_estado = data.get("estado", "Aprobado")
    reserva.estado_reserva = nuevo_estado
    
    qr_links = []
    if nuevo_estado.lower() in ["aprobado", "aprobada"]:
        existentes = db.query(IngresoPuerta).filter(IngresoPuerta.reserva_id == reserva.id).all()
        
        if not existentes:
            total_pases = int(reserva.cantidad_personas or 1)
            for i in range(1, total_pases + 1):
                cedula_cliente = reserva.cliente.cedula if reserva.cliente and reserva.cliente.cedula else "S/C"
                token_qr = f"{reserva.codigo_reserva}-CC-{cedula_cliente}-PASS-{i}-{uuid.uuid4().hex[:4]}"
                
                nuevo_ingreso = IngresoPuerta(
                    reserva_id=reserva.id,
                    codigo_qr=token_qr,
                    estado_ingreso="no_utilizado"
                )
                db.add(nuevo_ingreso)
                
                qr_url_grafico = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={token_qr}"
                qr_links.append({"pase": i, "token": token_qr, "qr_img": qr_url_grafico})
            db.commit()
        else:
            for ing in existentes:
                qr_url_grafico = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={ing.codigo_qr}"
                qr_links.append({"token": ing.codigo_qr, "qr_img": qr_url_grafico})

    db.commit()

    cliente = reserva.cliente
    telefono_cliente = cliente.telefono if cliente and cliente.telefono else "593999999999"
    telefono_limpio = ''.join(filter(str.isdigit, telefono_cliente))
    if not telefono_limpio.startswith("593"):
        telefono_limpio = "593" + telefono_limpio.lstrip('0')

    evento = reserva.evento
    evento_nombre = evento.nombre_evento if evento else (reserva.nombre_personalizado or "Celebración Salsoteca")
    fecha_evento = evento.fecha_hora.strftime("%Y-%m-%d %H:%M") if evento and evento.fecha_hora else (reserva.fecha_personalizada or "Fecha por confirmar")
    cliente_nombre = cliente.nombre if cliente else "Cliente"
    cedula_txt = cliente.cedula if cliente and cliente.cedula else "No registrada"

    texto_whatsapp = (
        f"¡Hola *{cliente_nombre}*! 🎶✨\n\n"
        f"¡Excelentes noticias! Tu reserva para *{evento_nombre}* ha sido *APROBADA* ✅.\n\n"
        f"📅 *Fecha:* {fecha_evento}\n"
        f"🆔 *Cédula:* {cedula_txt}\n"
        f"📋 *Código de Reserva:* `{reserva.codigo_reserva}`\n"
        f"• Pases: {reserva.cantidad_personas} | Mesas: {reserva.cantidad_mesas}\n"
        f"• Total Cancelado: ${reserva.monto_total}\n\n"
        f"🎟️ *Tus códigos QR de acceso individual en puerta:*\n"
    )

    for idx, item in enumerate(qr_links, 1):
        texto_whatsapp += f"Pase #{idx}: {item['qr_img']}\n"

    texto_whatsapp += (
        f"\n¡Muchas gracias por preferirnos! Presenta estos códigos QR al ingresar al local. ¡Te esperamos para disfrutar! 🎷🔥"
    )

    whatsapp_url = f"https://wa.me/{telefono_limpio}?text={urllib.parse.quote(texto_whatsapp)}"

    return {
        "mensaje": "Reserva aprobada, códigos QR de puerta generados y listos para enviar",
        "estado": reserva.estado_reserva,
        "whatsapp_url": whatsapp_url,
        "qr_codes": qr_links
    }
    
@app.delete("/api/admin/locales/{local_id}")
def eliminar_local(local_id: int, db: Session = Depends(get_db)):
    local = db.query(Local).filter(Local.id == local_id).first()
    if not local:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    db.delete(local)
    db.commit()
    return {"mensaje": "Local eliminado correctamente"}