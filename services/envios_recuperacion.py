import smtplib
import ssl
from email.message import EmailMessage

from config.recuperacion import configuracion


class ErrorEnvioRecuperacion(ValueError):
    def __init__(self, motivo):
        self.motivo = motivo
        super().__init__('El proveedor no confirmó el envío. Revisa la configuración de correo.')


class EnviosRecuperacion:
    """Recuperación únicamente por correo mediante SMTP cifrado."""

    def __init__(self, config=None):
        self.config = config if config is not None else configuracion()

    def disponibles(self):
        c = self.config
        secreto = len(c.get('secreto', '')) >= 32
        correo = (c.get('correo_habilitado') and c.get('smtp_seguridad') in ('ssl', 'starttls')
                  and str(c.get('smtp_port', '')).isdigit()
                  and 1 <= int(c['smtp_port']) <= 65535
                  and all(c.get(k) for k in ('smtp_host', 'smtp_usuario', 'smtp_password', 'smtp_desde')))
        return {'correo': bool(secreto and correo)}

    def enviar(self, canal, destino, codigo):
        if canal != 'correo':
            raise ValueError('La recuperación solo está disponible por correo electrónico.')
        if not self.disponibles()['correo']:
            raise ErrorEnvioRecuperacion('configuracion')
        try:
            self._correo(destino, codigo)
        except ErrorEnvioRecuperacion:
            raise
        except smtplib.SMTPAuthenticationError:
            raise ErrorEnvioRecuperacion('autenticacion') from None
        except smtplib.SMTPRecipientsRefused:
            raise ErrorEnvioRecuperacion('destinatario') from None
        except smtplib.SMTPSenderRefused:
            raise ErrorEnvioRecuperacion('remitente') from None
        except (ssl.SSLError, smtplib.SMTPNotSupportedError):
            raise ErrorEnvioRecuperacion('tls') from None
        except (OSError, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError):
            raise ErrorEnvioRecuperacion('conexion') from None
        except Exception:
            # Ni el código, los tokens ni las respuestas del proveedor llegan al log o la interfaz.
            raise ErrorEnvioRecuperacion('proveedor') from None

    def _correo(self, destino, codigo):
        c = self.config
        mensaje = EmailMessage()
        mensaje['Subject'] = 'Zeyver · Código para recuperar tu contraseña'
        mensaje['From'], mensaje['To'] = c['smtp_desde'], destino
        mensaje.set_content(
            f'Tu código de Zeyver es: {codigo}\n\n'
            'Tu solicitud y este código caducan en 3 horas. No lo compartas.\n'
            'Un administrador autorizó tu solicitud. Valida este código para establecer la nueva contraseña.\n'
            'La vigencia se cuenta desde tu solicitud, no desde este correo.\n'
            'Si cierras la ventana, vuelve al login y elige Retomar con mi código.\n'
            'Solo permite completar un cambio de contraseña.\n'
            'Si no hiciste esta solicitud, ignora este mensaje. Tu contraseña no ha cambiado.'
        )
        contexto = ssl.create_default_context()
        if c['smtp_seguridad'] == 'ssl':
            cliente = smtplib.SMTP_SSL(c['smtp_host'], int(c['smtp_port']), timeout=15, context=contexto)
        else:
            cliente = smtplib.SMTP(c['smtp_host'], int(c['smtp_port']), timeout=15)
        with cliente:
            if c['smtp_seguridad'] == 'starttls':
                cliente.ehlo()
                cliente.starttls(context=contexto)
                cliente.ehlo()
            cliente.login(c['smtp_usuario'], c['smtp_password'])
            if cliente.send_message(mensaje):
                raise ErrorEnvioRecuperacion('destinatario')
