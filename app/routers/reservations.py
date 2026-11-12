import os
import re
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.r2_storage import upload_file_to_r2

router = APIRouter(prefix="/api/reservas", tags=["Reservas"])

# ==========================================
# GESTIÓN DE EVENTOS Y CARTELERA
# ==========================================

@router.get("/eventos/")
def listar_eventos(local_id: int = 1, db: Session = Depends(get_db)):
    """Obtiene la lista de eventos activos para un local específico"""
    eventos = db.query(models.Evento).filter(models.Evento.local_id == local_id).all()
    return eventos

@router.post("/eventos/")
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
    """Crea un nuevo evento con tarifas y sube su flyer/póster directamente a Cloudflare R2"""
    imagen_nombre = None
    
    if file and file.filename:
        file_extension = file.filename.split(".")[-1]
        imagen_nombre = f"evento_{uuid.uuid4()}.{file_extension}"
        
        # Subir a Cloudflare R2
        upload_file_to_r2(
            file_obj=file.file,
            filename=imagen_nombre,
            content_type=file.content_type
        )

    nuevo_evento = models.Evento(
        local_id=local_id,
        nombre_evento=nombre_evento,
        artista_orquesta=artista_orquesta,
        fecha_hora=fecha_hora,
        descripcion=descripcion,
        imagen=imagen_nombre,
        estado=estado,
        precio_cover=precio_cover,
        precio_mesa=precio_mesa,
        descripcion_mesa=descripcion_mesa,
        precio_promocion=precio_promocion,
        descripcion_promocion=descripcion_promocion
    )
    
    db.add(nuevo_evento)
    db.commit()
    db.refresh(nuevo_evento)
    return {"mensaje": "Evento creado exitosamente con tarifas y R2", "id": nuevo_evento.id}

@router.put("/eventos/{evento_id}")
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
    """Actualiza los datos, tarifas y el flyer en Cloudflare R2 de un evento existente"""
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if nombre_evento is not None:
        evento.nombre_evento = nombre_evento
    if artista_orquesta is not None:
        evento.artista_orquesta = artista_orquesta
    if fecha_hora is not None and fecha_hora != "":
        evento.fecha_hora = fecha_hora
    if descripcion is not None:
        evento.descripcion = descripcion

    # Actualizar tarifas y descripciones de reservas
    evento.precio_cover = precio_cover
    evento.precio_mesa = precio_mesa
    evento.descripcion_mesa = descripcion_mesa
    evento.precio_promocion = precio_promocion
    evento.descripcion_promocion = descripcion_promocion

    # Si se adjunta una nueva imagen de póster, se sube a R2
    if file and file.filename:
        file_extension = file.filename.split(".")[-1]
        imagen_nombre = f"evento_{uuid.uuid4()}.{file_extension}"
        
        upload_file_to_r2(
            file_obj=file.file,
            filename=imagen_nombre,
            content_type=file.content_type
        )
        evento.imagen = imagen_nombre

    db.commit()
    db.refresh(evento)
    return {"mensaje": "Evento actualizado correctamente en R2", "id": evento.id}

@router.delete("/eventos/{evento_id}")
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    """Elimina un evento de la cartelera"""
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    db.delete(evento)
    db.commit()
    return {"mensaje": "Evento eliminado correctamente"}


# ==========================================
# GESTIÓN DE RESERVAS Y COMPROBANTES
# ==========================================

@router.post("/con_comprobante/")
async def crear_reserva_con_comprobante(
    evento_id: int = Form(...),
    cliente_id: int = Form(1),
    cliente_nombre: str = Form("Cliente Web"),
    cliente_telefono: str = Form("0999999999"),
    cantidad_personas: int = Form(1),  # Covers / Pases
    cantidad_mesas: int = Form(0),      # Mesas apartadas
    monto_total: float = Form(0.0),     # Valor total calculado en dinero
    tipo_reserva: str = Form("Cover"),  # Ej: "2 Covers + 1 Mesa"
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Crea una nueva solicitud de reserva combinada enviando el comprobante directamente a Cloudflare R2"""
    file_extension = file.filename.split(".")[-1]
    nombre_limpio = f"comprobante_{uuid.uuid4()}.{file_extension}"

    # Subir comprobante a Cloudflare R2
    upload_file_to_r2(
        file_obj=file.file,
        filename=nombre_limpio,
        content_type=file.content_type
    )

    # Verificar o registrar el cliente utilizando UsuarioFinal
    cliente = db.query(models.UsuarioFinal).filter(models.UsuarioFinal.telefono == cliente_telefono).first()
    if not cliente:
        cliente = models.UsuarioFinal(
            nombre=cliente_nombre,
            telefono=cliente_telefono,
            email=f"cliente_{int(datetime.utcnow().timestamp())}@salsoteca.com",
            password_hash="temp_hash_web"
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    codigo_aleatorio = f"RES-{int(datetime.utcnow().timestamp())}"

    nueva_reserva = models.Reserva(
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
        "mensaje": "Reserva combinada creada exitosamente con comprobante en R2",
        "reserva_id": nueva_reserva.id,
        "monto_total": float(nueva_reserva.monto_total),
        "estado": nueva_reserva.estado_reserva,
        "comprobante": nombre_limpio
    }