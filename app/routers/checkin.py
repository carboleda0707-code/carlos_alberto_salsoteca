# -*- coding: utf-8 -*-
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import IngresoPuerta, Reserva, UsuarioFinal, Evento, Usuario

router = APIRouter(prefix="/api/checkin", tags=["Control de Puerta CheckIn"])

@router.get("/estadisticas/")
def obtener_estadisticas_puerta(db: Session = Depends(get_db)):
    total_emitidos = db.query(IngresoPuerta).count()
    total_validados = db.query(IngresoPuerta).filter(IngresoPuerta.estado_ingreso == "AL").count()
    total_pendientes = db.query(IngresoPuerta).filter(
        (IngresoPuerta.estado_ingreso == "PE") | 
        (IngresoPuerta.estado_ingreso == "no_utilizado") |
        (IngresoPuerta.estado_ingreso == None) |
        (IngresoPuerta.fecha_ingreso == None)
    ).count()
    return {
        "emitidos": total_emitidos,
        "validados": total_validados,
        "pendientes": total_pendientes
    }

@router.get("/fechas-eventos/")
def listar_fechas_y_eventos(db: Session = Depends(get_db)):
    """Retorna eventos agrupados por fecha con los datos del creador (Nombre, Celular, Cédula)"""
    eventos = db.query(Evento).order_by(Evento.fecha_hora.desc()).all()
    resultado = []
    
    for ev in eventos:
        fecha_str = ev.fecha_hora.strftime('%Y-%m-%d') if ev.fecha_hora else "Sin Fecha"
        
        creador_nombre = "Administración"
        creador_telefono = ""
        creador_cedula = ""
        
        if ev.creador:
            cli = db.query(UsuarioFinal).filter(UsuarioFinal.id == ev.creador).first()
            if cli:
                creador_nombre = cli.nombre
                creador_telefono = cli.telefono or ""
                creador_cedula = getattr(cli, 'cedula', '') or ""
            else:
                usr = db.query(Usuario).filter(Usuario.propietario_id == ev.creador).first()
                if usr:
                    creador_nombre = usr.nombre
                    creador_telefono = usr.correo or ""
                    creador_cedula = ""

        reservas_ev = db.query(Reserva).filter(Reserva.evento_id == ev.id).all()
        reserva_ids = [r.id for r in reservas_ev]
        
        pases_emitidos = 0
        pases_validados = 0
        if reserva_ids:
            pases_emitidos = db.query(IngresoPuerta).filter(IngresoPuerta.reserva_id.in_(reserva_ids)).count()
            pases_validados = db.query(IngresoPuerta).filter(
                IngresoPuerta.reserva_id.in_(reserva_ids),
                IngresoPuerta.estado_ingreso == "AL"
            ).count()

        resultado.append({
            "evento_id": ev.id,
            "nombre_evento": ev.nombre_evento,
            "artista_orquesta": ev.artista_orquesta or "",
            "fecha_hora": ev.fecha_hora.strftime('%Y-%m-%d %H:%M') if ev.fecha_hora else "",
            "fecha": fecha_str,
            "creador_nombre": creador_nombre,
            "creador_telefono": creador_telefono,
            "creador_cedula": creador_cedula,
            "pases_emitidos": pases_emitidos,
            "pases_validados": pases_validados
        })
        
    return resultado

@router.get("/evento/{evento_id}/qrs")
def obtener_qrs_por_evento(evento_id: int, db: Session = Depends(get_db)):
    """Retorna los QR de las reservas aprobadas para un evento específico"""
    reservas = db.query(Reserva).filter(Reserva.evento_id == evento_id).all()
    reserva_ids = [r.id for r in reservas]
    
    if not reserva_ids:
        return []
        
    ingresos = db.query(IngresoPuerta).filter(IngresoPuerta.reserva_id.in_(reserva_ids)).all()
    
    lista = []
    for ing in ingresos:
        res = ing.reserva
        cli = res.cliente if res else None
        lista.append({
            "codigo_qr": ing.codigo_qr,
            "estado_ingreso": ing.estado_ingreso,
            "fecha_ingreso": ing.fecha_ingreso.strftime('%Y-%m-%d %H:%M:%S') if ing.fecha_ingreso else None,
            "codigo_reserva": res.codigo_reserva if res else "",
            "cliente_nombre": cli.nombre if cli else "Cliente",
            "cliente_telefono": cli.telefono if cli else "",
            "cliente_cedula": getattr(cli, 'cedula', 'S/C') if cli else 'S/C',
            "tipo_reserva": res.tipo_reserva if res else "Cover",
            "monto_total": float(res.monto_total) if res else 0.0
        })
        
    return lista

@router.get("/historial/")
def obtener_historial_accesos(db: Session = Depends(get_db)):
    ingresos = db.query(IngresoPuerta).order_by(IngresoPuerta.fecha_ingreso.desc()).limit(20).all()
    resultado = []
    for ing in ingresos:
        reserva = ing.reserva
        cliente = reserva.cliente if reserva else None
        evento = reserva.evento if reserva else None
        resultado.append({
            "hora_ingreso": ing.fecha_ingreso.strftime('%Y-%m-%d %H:%M:%S') if ing.fecha_ingreso else "Pendiente",
            "codigo_qr": ing.codigo_qr,
            "cliente": cliente.nombre if cliente else "Desconocido",
            "cedula": getattr(cliente, 'cedula', 'S/C') if cliente else 'S/C',
            "evento": evento.nombre_evento if evento else "Salsoteca C.A.",
            "estado": ing.estado_ingreso
        })
    return resultado

@router.post("/escanear/")
def escanear_qr_puerta(data: dict, db: Session = Depends(get_db)):
    codigo_qr = data.get("codigo_qr")
    if not codigo_qr:
        raise HTTPException(status_code=400, detail="No se proporcionó el código QR.")
    ingreso = db.query(IngresoPuerta).filter(IngresoPuerta.codigo_qr == codigo_qr.strip()).first()
    if not ingreso:
        raise HTTPException(status_code=404, detail="❌ Código QR no encontrado o inválido.")
    if ingreso.estado_ingreso == "AL":
        return {
            "valido": False,
            "mensaje": f"⚠️ ATENCIÓN: Este pase QR ya se encuentra Adentro Local (AL) desde el {ingreso.fecha_ingreso.strftime('%Y-%m-%d %H:%M') if ingreso.fecha_ingreso else 'anteriormente'}.",
            "cliente": ingreso.reserva.cliente.nombre if ingreso.reserva and ingreso.reserva.cliente else "Desconocido"
        }
    ingreso.estado_ingreso = "AL"
    ingreso.fecha_ingreso = datetime.utcnow()
    db.commit()
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