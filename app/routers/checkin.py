from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import IngresoPuerta, Reserva, UsuarioFinal, Evento

router = APIRouter(prefix="/api/checkin", tags=["Control de Puerta CheckIn"])

@router.post("/escanear/")
def escanear_qr_puerta(data: dict, db: Session = Depends(get_db)):
    """
    Recibe el código QR escaneado en puerta, valida su existencia,
    comprueba si ya ingresó al local y registra el acceso (PE -> AL).
    """
    codigo_qr = data.get("codigo_qr")
    if not codigo_qr:
        raise HTTPException(status_code=400, detail="No se proporcionó el código QR.")

    # Buscar el registro del QR en la base de datos
    ingreso = db.query(IngresoPuerta).filter(IngresoPuerta.codigo_qr == codigo_qr).first()
    if not ingreso:
        raise HTTPException(status_code=404, detail="❌ Código QR no encontrado o inválido.")

    # Verificar si ya fue utilizado (Estatus AL - Adentro Local)
    if ingreso.estado_ingreso == "AL":
        return {
            "valido": False,
            "mensaje": f"⚠️ ATENCIÓN: Este pase QR ya se encuentra Adentro Local (AL) desde el {ingreso.fecha_ingreso.strftime('%Y-%m-%d %H:%M') if ingreso.fecha_ingreso else 'anteriormente'}.",
            "cliente": ingreso.reserva.cliente.nombre if ingreso.reserva and ingreso.reserva.cliente else "Desconocido"
        }

    # Marcar como Adentro Local (AL) y registrar la hora actual
    ingreso.estado_ingreso = "AL"
    ingreso.fecha_ingreso = datetime.utcnow()
    db.commit()

    # Obtener datos para mostrar en la interfaz de puerta
    reserva = ingreso.reserva
    cliente = reserva.cliente if reserva else None
    evento = reserva.evento if reserva else None

    return {
        "valido": True,
        "mensaje": "✅ ¡Acceso Autorizado con Éxito (Adentro Local)!",
        "detalles": {
            "cliente_nombre": cliente.nombre if cliente else "Cliente",
            "cliente_cedula": getattr(cliente, 'cedula', 'S/C'),
            "cliente_telefono": cliente.telefono if cliente else "",
            "evento_nombre": evento.nombre_evento if evento else "Evento Salsoteca",
            "codigo_reserva": reserva.codigo_reserva if reserva else "",
            "tipo_reserva": reserva.tipo_reserva if reserva else "Cover",
            "pases": reserva.cantidad_personas if reserva else 1,
            "mesas": reserva.cantidad_mesas if reserva else 0,
            "hora_ingreso": ingreso.fecha_ingreso.strftime("%H:%M:%S")
        }
    }