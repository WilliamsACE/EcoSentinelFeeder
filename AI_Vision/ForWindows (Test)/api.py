"""
api.py
------
Servidor FastAPI. Se ejecuta en un hilo daemon desde main.py.

Endpoints:
  POST  /dispenser/trigger   dispara el dispensador manualmente
  GET   /config              consulta la configuracion actual
  PATCH /config              actualiza parametros en vivo
  POST  /debug/on            activa la ventana de debug
  POST  /debug/off           desactiva la ventana de debug
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

import config
from dispenser import requestDispenser

app = FastAPI(title="Pet Dispenser API", version="1.0.0")


# ── Modelos ───────────────────────────────────────────────────────────────────

class TriggerRequest(BaseModel):
    animal: Literal["cat", "dog", "person"] = Field(
        description="Animal a dispensar"
    )


class ConfigUpdate(BaseModel):
    min_confidence: Optional[float] = Field(
        default=None, ge=0.1, le=1.0,
        description="Confianza minima de YOLO (0.1 - 1.0)"
    )
    min_confirmations: Optional[int] = Field(
        default=None, ge=1, le=4,
        description="Fotos minimas que deben confirmar (1 - 4)"
    )
    min_contour_area: Optional[int] = Field(
        default=None, ge=100,
        description="Area minima de contorno en px^2"
    )
    cooldown: Optional[float] = Field(
        default=None, ge=1.0, le=60.0,
        description="Segundos de pausa tras cada evento (1 - 60)"
    )
    capture_interval: Optional[float] = Field(
        default=None, ge=0.1, le=2.0,
        description="Segundos entre cada foto (0.1 - 2.0)"
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/dispenser/trigger", summary="Disparar dispensador manualmente")
def trigger_dispenser(body: TriggerRequest):
    """Llama a requestDispenser() sin pasar por deteccion."""
    try:
        requestDispenser(body.animal)
        return {"status": "ok", "message": f"Dispensador activado para {body.animal}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config", summary="Consultar configuracion actual")
def get_config():
    return config.snapshot()


@app.patch("/config", summary="Actualizar parametros en vivo")
def patch_config(update: ConfigUpdate):
    """
    Actualiza uno o varios parametros sin reiniciar el sistema.
    Solo enviar los campos que quieres cambiar.
    """
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No se envio ningun parametro")
    updated = config.update(changes)
    return {"status": "ok", "config": updated}


@app.post("/debug/on", summary="Activar ventana de debug")
def debug_on():
    """Abre una ventana mostrando el feed de la camara en tiempo real."""
    config.update({"debug": True})
    return {"status": "ok", "debug": True}


@app.post("/debug/off", summary="Desactivar ventana de debug")
def debug_off():
    """Cierra la ventana de debug y retoma el loop de deteccion."""
    config.update({"debug": False})
    return {"status": "ok", "debug": False}