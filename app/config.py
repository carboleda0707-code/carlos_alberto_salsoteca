import configparser
import json
from pathlib import Path

# Directorio actual donde está config.py (la carpeta app)
BASE_DIR = Path(__file__).resolve().parent

# Cargar el archivo config.ini desde la misma carpeta app
config = configparser.ConfigParser()
config_path = BASE_DIR / "config.ini"

if config_path.exists():
    config.read(config_path, encoding="utf-8")
else:
    raise FileNotFoundError(f"No se encontró el archivo de configuración en: {config_path}")

# ==========================================
# CONFIGURACIÓN DEL SISTEMA
# ==========================================
APP_TITLE = config.get("system", "app_title", fallback="Salsoteca Carlos Alberto")
SUPERADMIN_NAME = config.get("system", "superadmin_name", fallback="Carlos Arboleda")
VERSION = config.get("system", "version", fallback="1.0.0")
ENVIRONMENT = config.get("system", "environment", fallback="production")

# ==========================================
# CONFIGURACIÓN DE APIS Y ENDPOINTS
# ==========================================
LOCAL_URL = config.get("api", "local_url", fallback="http://127.0.0.1:8000")
APPS_ENDPOINT = config.get("api", "apps_endpoint", fallback="/api/apps/")
R2_STATUS_ENDPOINT = config.get("api", "r2_status_endpoint", fallback="/api/v1/r2/status")

# ==========================================
# VALORES POR DEFECTO Y MÉTRICAS
# ==========================================
CURRENCY = config.get("defaults", "currency", fallback="USD")
EGRESS_SAVINGS = config.get("defaults", "egress_savings", fallback="$0.00 USD")
ACTIVE_APPS_COUNT = config.get("defaults", "active_apps_count", fallback="3 Activas")

# ==========================================
# TARIFAS OFICIALES DEL SISTEMA (COVERS Y MESAS)
# ==========================================
PRECIO_COVER = config.getfloat("defaults", "precio_cover", fallback=10.00)
PRECIO_MESA = config.getfloat("defaults", "precio_mesa", fallback=50.00)

def obtener_tarifas_sistema():
    """
    Retorna un diccionario con las tarifas vigentes de covers y mesas
    leídas directamente desde el archivo de configuración config.ini.
    """
    return {
        "precio_cover": PRECIO_COVER,
        "precio_mesa": PRECIO_MESA
    }

# ==========================================
# CARGADOR DINÁMICO DE APLICACIONES
# ==========================================
def obtener_aplicaciones_registradas():
    """
    Lee dinámicamente el archivo apps_seed.json para listar todas las plataformas
    integradas en el Superadmin Hub.
    """
    json_path = BASE_DIR / "apps_seed.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []