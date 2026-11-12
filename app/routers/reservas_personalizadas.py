import re
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Evento, UsuarioFinal, Reserva
from app.r2_storage import upload_file_to_r2

router = APIRouter(prefix="/api/clientes/eventos", tags=["Eventos y Reservas Personalizadas del Cliente"])

@router.post("/crear/")
async def crear_evento_y_reserva_personalizada(
    local_id: int = Form(1),
    cliente_nombre: str = Form(...),
    cliente_cedula: str = Form(...),
    cliente_telefono: str = Form(...),
    cliente_email: str = Form(...),
    nombre_evento: str = Form(...),
    tipo_celebracion: str = Form("Cumpleaños"),
    fecha_hora: str = Form(...),
    cantidad_personas: int = Form(1),
    cantidad_mesas: int = Form(0),
    monto_total: float = Form(0.0),
    file_flyer: UploadFile = File(None),
    file_comprobante: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. Subir Flyer personalizado directamente a Cloudflare R2
        imagen_evento_nombre = "evento_default.jpg"
        if file_flyer and file_flyer.filename:
            file_extension = Path(file_flyer.filename).suffix
            imagen_evento_nombre = f"cliente_evento_{uuid.uuid4().hex[:8]}{file_extension}"
            
            upload_file_to_r2(
                file_obj=file_flyer.file,
                filename=imagen_evento_nombre,
                content_type=file_flyer.content_type
            )

        # 2. Subir Comprobante de pago directamente a Cloudflare R2
        comp_extension = Path(file_comprobante.filename).suffix
        comprobante_nombre = f"comp_per_{uuid.uuid4().hex[:8]}{comp_extension}"
        
        upload_file_to_r2(
            file_obj=file_comprobante.file,
            filename=comprobante_nombre,
            content_type=file_comprobante.content_type
        )

        # 3. Registrar o actualizar cliente
        cliente = db.query(UsuarioFinal).filter((UsuarioFinal.cedula == cliente_cedula) | (UsuarioFinal.email == cliente_email)).first()
        if not cliente:
            cliente = UsuarioFinal(
                nombre=cliente_nombre,
                cedula=cliente_cedula,
                email=cliente_email,
                telefono=cliente_telefono,
                password_hash="temp_cliente"
            )
            db.add(cliente)
            db.commit()
            db.refresh(cliente)

        # 4. Parsear fecha
        fecha_limpia = fecha_hora.replace('T', ' ')
        if len(fecha_limpia) == 16: fecha_limpia += ":00"
        fecha_dt = datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")

        # 5. Registrar el Evento en la Cartelera de la Salsoteca
        nuevo_evento = Evento(
            local_id=local_id,
            nombre_evento=nombre_evento,
            artista_orquesta=f"Celebración: {tipo_celebracion} de {cliente_nombre}",
            genero_musical="Celebración Privada",
            fecha_hora=fecha_dt,
            descripcion=f"Evento personalizado creado por {cliente_nombre}. ¡Acompáñanos!",
            imagen=imagen_evento_nombre,
            estado="programado",
            precio_cover=10.00,
            precio_mesa=50.00
        )
        db.add(nuevo_evento)
        db.commit()
        db.refresh(nuevo_evento)

        # 6. Crear la Reserva asociada con estado "Por Aprobar"
        codigo_reserva = f"RES-PER-{int(datetime.utcnow().timestamp())}"
        nueva_reserva = Reserva(
            evento_id=nuevo_evento.id,
            cliente_id=cliente.id,
            cantidad_personas=cantidad_personas,
            cantidad_mesas=cantidad_mesas,
            monto_total=monto_total,
            tipo_reserva=f"Personalizada - {tipo_celebracion}",
            tipo_celebracion=tipo_celebracion,
            codigo_reserva=codigo_reserva,
            comprobante_pago=comprobante_nombre,
            estado_reserva="Por Aprobar"
        )
        db.add(nueva_reserva)
        db.commit()
        db.refresh(nueva_reserva)

        return {
            "exito": True,
            "mensaje": "¡Tu evento y solicitud de reserva personalizada han sido enviados con éxito a R2 para aprobación!",
            "codigo_reserva": codigo_reserva
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))