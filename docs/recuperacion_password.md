# Recuperación de contraseña con aprobación · Zeyver

## Flujo

1. En el login, **¿Olvidaste tu contraseña? → Solicitar recuperación** registra
   una solicitud **En espera de autorización**. No se genera código ni se contacta
   con SMTP en este paso; se puede solicitar incluso si el correo no está configurado.
2. La solicitud queda confirmada en PostgreSQL. El usuario puede cerrar la ventana,
   salir del sistema o entrar con otra cuenta: no se cancela ni se borra.
   Si su cuenta no tiene correo, también se guarda: el administrador verá
   **Falta registrar correo**. Puede denegarla o registrar el correo en
   **Usuarios → Editar acceso** y actualizar la bandeja para habilitar la autorización.
   No se genera ni envía código a un destino vacío. El plazo original no se amplía.
3. Un **administrador activo diferente del solicitante** autoriza o deniega desde
   **Gestión de usuarios → Solicitudes de contraseña**, en una pestaña del mismo módulo.
   No necesita esperar una validación previa del código ni ve códigos o contraseñas.
4. **Solo después de autorizar**, se genera un código aleatorio de **8 letras y
   números** con `secrets` y se intenta enviar al correo registrado del usuario.
   La autorización se confirma antes de contactar a SMTP. Si deniega, no se envía nada.
5. El solicitante valida el código o vuelve al login y elige **Retomar con mi código**.
   Solo después de probar que posee el código autorizado se habilita la contraseña
   nueva de **6 a 128 caracteres**. El estado se consulta cada 10 segundos mientras
   la ventana de espera permanece abierta.

Solicitud y código mantienen una vigencia máxima de **3 horas desde la petición**,
con **5 intentos** de código. Autorizar o retomar no amplía el plazo. Solo se puede
completar un cambio de contraseña. El acceso inicial de seguimiento y la autorización
del administrador **no bastan para cambiar la contraseña sin validar el código**.

El administrador ve un contador de pendientes en Gestión de usuarios y en la pestaña
de solicitudes, además de un aviso dentro de Zeyver. No hay un apartado separado
en la barra lateral ni una ventana independiente para revisar estas solicitudes.
Se consulta cada 30 segundos con la aplicación abierta y al iniciar sesión.
La bandeja visible se refresca incluso si el contador no cambia. Cada fila conserva
su solicitud; varias peticiones de la misma persona no se agrupan en una sola.
La tabla es el **historial completo**, sin filtro por estado ni recorte de 100 filas:
autorizar, denegar, completar o caducar una solicitud no la quita del historial.
Se presenta en páginas de **7 filas**: desde 7 registros aparece el pie con el rango,
la página actual y los botones **Anterior / Siguiente**. No se descartan registros
al cambiar de página. El resto de las tablas usa el mismo componente de paginación.
Incluye referencia, estado, fecha de solicitud, administrador y fecha de decisión.
El resumen distingue el total histórico de las solicitudes por revisar; el contador
de la pestaña y de la navegación indica únicamente las que están **por revisar**.
Gestión de usuarios usa controles nativos, sin embeberlos en una escena escalada.
Las confirmaciones de eliminar, autorizar y denegar son no bloqueantes:
**Cancelar**, **Escape** y la **X** cierran sin ejecutar la acción. Solo el botón
de confirmación la envía al controlador.
Las solicitudes persisten si se cierra la aplicación; **no son notificaciones
externas ni avisos push con la aplicación cerrada**.

Al cerrar la ventana se borra el acceso local, **no la solicitud de PostgreSQL**.
Para continuar después de entrar/salir como administrador o reiniciar la aplicación:
introducir el usuario en el login, elegir **Retomar con mi código** y escribir el
mismo código del correo. Se vuelve a validar el código y se emite un acceso nuevo;
el anterior deja de servir. Si el administrador autorizó y se envió el correo, el
código se valida y se muestra el formulario. Antes de autorizar no existe un código.
No se envía otro correo y el plazo original no se reinicia. Los intentos de retomar
cuentan para el mismo límite de cinco fallos. Una solicitud rechazada, bloqueada,
caducada o completada no puede retomarse.

Una nueva petición sin validar código no cancela una aprobación anterior.
El botón para pedir otro código muestra una cuenta regresiva de
**02:00** y se habilita al terminar. La espera también se verifica en PostgreSQL:
hay un máximo de **1 solicitud cada 2 minutos y 3 por hora por cuenta**, aunque se cierre
y vuelva a abrir el diálogo.
Las respuestas públicas no confirman si existe un usuario ni revelan sus contactos.
Si el proveedor falla, no se presenta una confirmación falsa de envío.
La bandeja separa **Solicitud** y **Correo**: una autorización puede quedar guardada
con correo **No enviado**, sin ser una solicitud denegada ni desaparecida. El
administrador ve una categoría de error segura (autenticación, TLS, conexión,
remitente, destinatario o proveedor) y puede usar **Reintentar envío** tras 2 minutos.
Se permiten **3 intentos SMTP por solicitud**. Si se interrumpe la aplicación durante
el envío, el registro permanece y se puede reintentar tras ese intervalo. Una
respuesta tardía de un envío anterior no confirma el código nuevo por accidente.

## Esquema único

La tabla `recuperaciones_password`, sus restricciones e índices se definen en
**`database/flamar_postgres.sql`**, junto a `usuarios`. Es nueva información (códigos
protegidos, estados, caducidades y aprobaciones), no otra copia de los contactos.
No hay un segundo archivo SQL ni creación automática de tablas al abrir la app.
La base configurada ya se actualizó para conservar solicitudes, decisiones y el
resultado del último intento de correo. Las solicitudes antiguas sin autorización
se trasladan a espera (o caducadas si ya vencieron), sin enviar mensajes ni aprobarlas.
Para una base nueva se usa el esquema general. **No ejecutar el esquema completo
ni repetir CREATE TABLE sobre una base existente con datos.**

## Activar envíos reales

**El único canal de recuperación es el correo electrónico. No se simulan envíos.**
El envío requiere configuración SMTP válida y activación explícita; **registrar una
solicitud no depende de SMTP, enviarla después de autorizar sí**.
Usar `config/recuperacion.env.example` como referencia y añadir las variables a
`config/.env` (no versionarlo ni compartirlo). Reiniciar después de cambiarlo.

Primero generar `RECOVERY_SECRET` con al menos 32 caracteres aleatorios:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Configuración SMTP

Se necesita un proveedor de correo con SMTP y TLS:

- `RECOVERY_SMTP_HOST`, `RECOVERY_SMTP_PORT`, `RECOVERY_SMTP_USER`,
  `RECOVERY_SMTP_PASSWORD` y `RECOVERY_SMTP_FROM` (remitente autorizado).
- `RECOVERY_SMTP_SECURITY=ssl` (habitualmente puerto 465) o `starttls`
  (habitualmente 587). No se admite SMTP sin cifrar ni certificados ignorados.
  Si no se indica el modo, el puerto 587 utiliza STARTTLS y el 465 utiliza SSL.
- Con Gmail, habilitar verificación en dos pasos y usar una contraseña de aplicación
  si la cuenta/política lo permite; no pegar la contraseña habitual de Gmail.
- Tras configurar, poner `RECOVERY_EMAIL_ENABLED=true` y hacer una prueba con un
  correo propio registrado. La aceptación SMTP no garantiza llegada a la bandeja:
  comprobar spam, remitente y límites del proveedor.

Referencia: [contraseñas de aplicación de Google](https://support.google.com/accounts/answer/185833).

El teléfono se conserva como dato de contacto, pero no se usa para recuperar
contraseñas ni se marca como verificado en este flujo. Las antiguas variables de
WhatsApp, si siguen en `config/.env`, se ignoran: no se necesita una cuenta de Meta.
El esquema conserva el identificador del canal anterior para no perder posibles
registros históricos; no se permiten nuevas solicitudes ni completar recuperaciones
por ese canal. No es necesario modificar la base de datos existente.

No se han contratado servicios ni enviado correos de prueba. Se comprobó la
autenticación SMTP de la configuración local, sin enviar mensajes. Las pruebas
automatizadas SMTP usan mocks, sin correos reales.

## Controles y límites de seguridad

- Código protegido con HMAC-SHA256 y secreto de configuración; identificador de
  acceso aleatorio de 256 bits, almacenado solo como SHA-256. No se guardan códigos
  ni contraseñas nuevas en texto plano, ni se registran cuerpos del proveedor.
- La prueba HMAC del código se conserva protegida durante la vigencia para poder
  retomar después de cerrar. Se elimina al completar, rechazar, bloquear o caducar;
  el código nunca permite dos cambios de contraseña. Cada reanudación rota el acceso.
- Aprobación y cambio final revalidan rol/estado en PostgreSQL. No hay autoaprobación.
  Se necesita otro administrador activo para recuperar la cuenta de un administrador.
  Si solo existe uno y pierde acceso, se requiere intervención del responsable de
  la base; no hay contraseña maestra ni bypass.
- El consumo del acceso, los intentos, límites y cambio de contraseña se serializan
  en transacciones. Cambiar el contacto o la contraseña por otro medio, desactivar
  la cuenta o revocar permisos del aprobador impide completar una solicitud antigua.
- El contacto se marca verificado únicamente al finalizar con éxito todo el flujo.
  Las demás solicitudes activas de esa cuenta se cancelan al cambiar la contraseña.
- **Arquitectura existente:** el escritorio se conecta directamente a PostgreSQL.
  Los controles protegen el flujo de la aplicación, pero no a alguien con acceso
  directo a sus credenciales de BD o a un cliente modificado. Para equipos no
  confiables o exposición a Internet se necesita un backend que custodie secretos,
  autentique administradores y aplique permisos y límites también por origen/IP.
- Las sesiones de escritorio ya abiertas no se revocan automáticamente: el proyecto
  no dispone de sesiones centralizadas. La recuperación no inicia sesión por sí sola.

## Pruebas

`python -B -m unittest discover -s tests -p "test_recuperacion*.py"`

Con `FLAMAR_TEST_DB=1`, las pruebas PostgreSQL cargan el esquema general en esquemas
aislados y revierten las transacciones. Una prueba de persistencia utiliza conexiones
físicamente distintas y confirma un esquema temporal que elimina al terminar.
Nunca se envían correos ni se cambian usuarios reales.
