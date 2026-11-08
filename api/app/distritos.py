"""Centro aproximado de cada distrito (lat, lon). Es la misma tabla que usa db/01_crear_y_cargar.sql.

La demo ubica al donante en el centro de su distrito; no se pide ni guarda su dirección.
"""
DISTRITOS: dict[str, tuple[float, float]] = {
    "Miraflores": (-12.1211, -77.0297),
    "San Isidro": (-12.0977, -77.0365),
    "Barranco": (-12.1497, -77.0219),
    "Surquillo": (-12.1128, -77.0103),
    "Santiago de Surco": (-12.1355, -76.9925),
    "San Borja": (-12.1050, -76.9990),
    "Lince": (-12.0838, -77.0350),
    "Jesús María": (-12.0745, -77.0460),
    "Magdalena del Mar": (-12.0905, -77.0700),
    "Pueblo Libre": (-12.0745, -77.0630),
    "San Miguel": (-12.0775, -77.0910),
    "La Victoria": (-12.0690, -77.0160),
    "Lima Cercado": (-12.0464, -77.0428),
    "Breña": (-12.0600, -77.0520),
    "Chorrillos": (-12.1690, -77.0230),
    "La Molina": (-12.0860, -76.9370),
    "Callao": (-12.0565, -77.1181),
}
