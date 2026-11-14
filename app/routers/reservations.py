# -*- coding: utf-8 -*-
import os
import re
import uuid
import json
import urllib.parse
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.r2_storage import upload_file_to_r2

router = APIRouter(prefix="/api", tags=["Reservas y Clientes"])

# ==========================================
# GESTIÓN DE CLIENTES (BÚSQUEDA POR CÉDULA)
# ==========================================

@router.get("/clientes/buscar/{cedula}")
def buscar_cliente_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Busca un cliente registrado por su cédula exacta para autocompletar el checkout"""
    cliente = db.query(models.UsuarioFinal).filter(
        models.UsuarioFinal.cedula == cedula.strip()
    ).first()
    
    if cliente:
        return {
            "encontrado": True,
            "nombre": cliente.nombre,
            "telefono": getattr(cliente, 'telefono', ''),
            "email": cliente.email,
            "mensaje": "¡Cliente encontrado!"
        }
    
    return {
        "encontrado": False,
        "mensaje": "Cliente nuevo."
    }


# ==========================================
# GESTIÓN DE EVENTOS Y CARTELERA
# ==========================================

@router.get("/reservas/eventos/")
def listar_eventos(local_id: int = 1, db: Session = Depends(get_db)):
    """Obtiene la lista de eventos activos para un local específico"""
    eventos = db.query(models.Evento).filter(models.Evento.local_id == local_id).all()
    return eventos

@router.post("/reservas/eventos/")
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
        file_extension = file.filename.split(".")[-1]
        imagen_nombre = f"evento_{uuid.uuid4()}.{file_extension}"
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

@router.put("/reservas/eventos/{evento_id}")
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
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if nombre_evento is not None: evento.nombre_evento = nombre_evento
    if artista_orquesta is not None: evento.artista_orquesta = artista_orquesta
    if fecha_hora is not None and fecha_hora != "": evento.fecha_hora = fecha_hora
    if descripcion is not None: evento.descripcion = descripcion

    evento.precio_cover = precio_cover
    evento.precio_mesa = precio_mesa
    evento.descripcion_mesa = descripcion_mesa
    evento.precio_promocion = precio_promocion
    evento.descripcion_promocion = descripcion_promocion

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

@router.delete("/reservas/eventos/{evento_id}")
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(evento)
    db.commit()
    return {"mensaje": "Evento eliminado correctamente"}


# ==========================================
# CHECKOUT MASIVO DE CARRITO
# ==========================================

@router.post("/checkout/carrito")
async def checkout_carrito(
    cedula: str = Form(...),
    nombre: str = Form(...),
    telefono: str = Form(...),
    email: str = Form(None),
    items_json: str = Form(...),
    mostrar_en_cartelera: str = Form("true"),
    comprobante: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        items = json.loads(items_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Formato de items JSON inválido.")

    if not items:
        raise HTTPException(status_code=400, detail="El carrito está vacío.")

    file_extension = comprobante.filename.split(".")[-1]
    nombre_comprobante = f"comprobante_{uuid.uuid4()}.{file_extension}"
    upload_file_to_r2(
        file_obj=comprobante.file,
        filename=nombre_comprobante,
        content_type=comprobante.content_type
    )

    cliente = db.query(models.UsuarioFinal).filter(
        (models.UsuarioFinal.telefono == telefono) | (models.UsuarioFinal.email == email)
    ).first()

    bool_cartelera = str(mostrar_en_cartelera).lower() in ["true", "1", "yes", "on"]

    if not cliente:
        cliente = models.UsuarioFinal(
            nombre=nombre,
            telefono=telefono,
            email=email or f"cliente_{int(datetime.utcnow().timestamp())}@salsoteca.com",
            password_hash="guest_checkout"
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    else:
        cliente.nombre = nombre
        cliente.telefono = telefono
        if email: cliente.email = email
        db.commit()

    reservas_creadas = []

    for item in items:
        evento_id = item.get("evento_id", 1)
        cant_covers = item.get("cantidad_covers", 0)
        cant_mesas = item.get("cantidad_mesas", 0)
        subtotal = item.get("subtotal", 0.0)
        
        if item.get("tipo") == "personalizado":
            estado_ev = "aprobado" if bool_cartelera else "programado"
            nuevo_evento_pers = models.Evento(
                local_id=1,
                nombre_evento=item.get("nombre_evento", "Mi Rumba"),
                artista_orquesta=item.get("tipo_celebracion", "Celebración"),
                fecha_hora=item.get("fecha_hora", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
                descripcion=f"Evento personalizado de {nombre}",
                estado=estado_ev  # Sincronizado con cartelera
            )
            db.add(nuevo_evento_pers)
            db.commit()
            db.refresh(nuevo_evento_pers)
            evento_id = nuevo_evento_pers.id

        codigo_reserva = f"RES-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:4]}"
        tipo_reserva_desc = f"{cant_covers} Covers + {cant_mesas} Mesas"

        nueva_reserva = models.Reserva(
            evento_id=evento_id,
            cliente_id=cliente.id,
            cantidad_personas=cant_covers,
            cantidad_mesas=cant_mesas,
            monto_total=subtotal,
            tipo_reserva=tipo_reserva_desc,
            comprobante_pago=nombre_comprobante,
            codigo_reserva=codigo_reserva,
            estado_reserva="Por Aprobar",
            mostrar_en_cartelera=bool_cartelera
        )
        db.add(nueva_reserva)
        db.commit()
        db.refresh(nueva_reserva)
        reservas_creadas.append(nueva_reserva.id)

    return {
        "exito": True,
        "mensaje": "🎉 ¡Solicitudes de reserva procesadas con éxito! Las revisaremos y te enviaremos tus QR por WhatsApp.",
        "reservas_ids": reservas_creadas
    }


# ==========================================
# APROBACIÓN, QR SEGUROS Y WHATSAPP WA.ME
# ==========================================

@router.post("/reservas/{reserva_id}/aprobar")
def aprobar_reserva_y_generar_qrs(reserva_id: int, db: Session = Depends(get_db)):
    """Aprueba la reserva, genera códigos QR en base de datos y arma el enlace de WhatsApp SIN mostrar los textos QR por seguridad"""
    reserva = db.query(models.Reserva).filter(models.Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    reserva.estado_reserva = "APROBADO"

    ingresos_existentes = db.query(models.IngresoPuerta).filter(models.IngresoPuerta.reserva_id == reserva.id).all()
    pases_generados = [ing.codigo_qr for ing in ingresos_existentes]
    total_pases = reserva.cantidad_personas or 1

    if not pases_generados:
        for i in range(total_pases):
            codigo_qr_unico = f"QR-{reserva.codigo_reserva}-{i+1}-{uuid.uuid4().hex[:4]}"
            nuevo_ingreso = models.IngresoPuerta(
                reserva_id=reserva.id,
                codigo_qr=codigo_qr_unico,
                estado_ingreso="PE"
            )
            db.add(nuevo_ingreso)
            pases_generados.append(codigo_qr_unico)

    db.commit()

    cliente_nombre = reserva.cliente.nombre if reserva.cliente and reserva.cliente.nombre else "Estimado Cliente"
    telefono_cliente = reserva.cliente.telefono if reserva.cliente and reserva.cliente.telefono else ""
    evento_nombre = reserva.evento.nombre_evento if getattr(reserva, "evento", None) else "Salsoteca Carlos Alberto"

    # MENSAJE DE WHATSAPP SEGURO (SIN EXPONER LOS CÓDIGOS QR EN EL TEXTO)
    mensaje_whatsapp = (
        f"🎉 ¡Hola *{cliente_nombre}*! Tu reserva en la *Salsoteca Carlos Alberto* "
        f"para *{evento_nombre}* (`{reserva.codigo_reserva}`) ha sido *APROBADA*.\n\n"
        f"✅ Tienes *{len(pases_generados)} pases aprobados* y tu(s) mesa(s) aseguradas.\n"
        f"📱 Tu ingreso en puerta será verificado con nuestros escáneres QR corporativos.\n\n"
        f"📍 ¡Te esperamos para vivir la mejor noche salsera en Guayaquil!"
    )

    telefono_limpio = "".join(filter(str.isdigit, str(telefono_cliente)))
    if telefono_limpio.startswith("0") and len(telefono_limpio) == 10:
        telefono_limpio = "593" + telefono_limpio[1:]
    elif not telefono_limpio.startswith("593") and len(telefono_limpio) == 9:
        telefono_limpio = "593" + telefono_limpio

    mensaje_codificado = urllib.parse.quote(mensaje_whatsapp)
    whatsapp_url = f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}" if telefono_limpio else ""

    return {
        "exito": True,
        "mensaje": "Reserva aprobada con éxito, códigos QR generados.",
        "whatsapp_url": whatsapp_url,
        "total_pases": len(pases_generados)
    }


@router.get("/reservas/{reserva_id}/qrs")
def obtener_qrs_reserva(reserva_id: int, db: Session = Depends(get_db)):
    ingresos = db.query(models.IngresoPuerta).filter(models.IngresoPuerta.reserva_id == reserva_id).all()
    
    resultado = []
    for ing in ingresos:
        resultado.append({
            "codigo_qr": ing.codigo_qr,
            "estatus": ing.estado_ingreso,
            "fecha_ingreso": ing.fecha_ingreso.strftime('%Y-%m-%d %H:%M:%S') if ing.fecha_ingreso else None
        })
        
    return resultado