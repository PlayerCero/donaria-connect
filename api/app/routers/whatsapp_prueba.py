from fastapi import APIRouter, Depends, HTTPException, status

from .. import whatsapp
from ..config import settings
from ..security import Usuario, requiere

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp (número de prueba)"])


@router.post("/prueba", summary="Enviar un aviso de ejemplo a los números de prueba (equipo)")
def prueba(usuario: Usuario = Depends(requiere("equipo"))) -> dict:
    if not whatsapp.configurado():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "WhatsApp no está configurado (faltan WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_NUMEROS_PRUEBA).")
    resultados = []
    for numero in settings.whatsapp_numeros_prueba:
        try:
            wamid = whatsapp.enviar_plantilla(numero, ["Clínica Delgado Auna", "O+", "2.4"])
            resultados.append({"numero": f"*****{numero[-4:]}", "enviado": True, "id": wamid})
        except whatsapp.ErrorWhatsApp as e:
            resultados.append({"numero": f"*****{numero[-4:]}", "enviado": False, "error": str(e)})
    return {"plantilla": settings.whatsapp_plantilla, "resultados": resultados}
