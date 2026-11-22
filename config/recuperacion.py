import os

# config.database carga config/.env al arrancar la aplicación.
from config import database  # noqa: F401


ESPERA_REENVIO_SEGUNDOS = 120
VIGENCIA_RECUPERACION_HORAS = 3


def configuracion():
    puerto = os.getenv('RECOVERY_SMTP_PORT', '465').strip()
    seguridad = os.getenv('RECOVERY_SMTP_SECURITY', '').strip().lower()
    if not seguridad:
        seguridad = 'starttls' if puerto == '587' else 'ssl'
    return {
        'secreto': os.getenv('RECOVERY_SECRET', ''),
        'correo_habilitado': os.getenv('RECOVERY_EMAIL_ENABLED', '').strip().lower() == 'true',
        'smtp_host': os.getenv('RECOVERY_SMTP_HOST', '').strip(),
        'smtp_port': puerto,
        'smtp_seguridad': seguridad,
        'smtp_usuario': os.getenv('RECOVERY_SMTP_USER', '').strip(),
        'smtp_password': os.getenv('RECOVERY_SMTP_PASSWORD', ''),
        'smtp_desde': os.getenv('RECOVERY_SMTP_FROM', '').strip(),
    }
