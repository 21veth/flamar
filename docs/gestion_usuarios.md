# Gestión de usuarios

Disponible al final de la navegación, después de Reportes y antes de Cerrar sesión,
únicamente para sesiones de administrador. Usa la tabla existente `public.usuarios`.
No incluye cuentas ni contraseñas de ejemplo. La definición de usuarios y sus campos
de contacto se mantiene únicamente en `database/flamar_postgres.sql`.

- Listar y buscar por usuario, correo o teléfono, filtrar por rol y estado, crear, modificar y eliminar.
- Roles disponibles: administrador, gerente y trabajador.
- El módulo reúne dos pestañas: **Usuarios** y **Solicitudes de contraseña**.
  Las aprobaciones y rechazos se gestionan en la segunda, con contador de pendientes.
- Editar usuarios no permite consultar ni cambiar contraseñas, tampoco enviándolas
  directamente al servicio. El repositorio de edición no actualiza `password_hash`.
- La cuenta propia no puede eliminarse, desactivarse ni perder su rol administrativo.
  Editarla requiere volver a iniciar sesión para actualizar las credenciales y la cabecera.
- Si el usuario tiene registros relacionados, el borrado se rechaza sin eliminar su historial;
  se puede desactivar en su lugar. La desactivación impide nuevos inicios de sesión.
- La sesión y el rol/estado actual en PostgreSQL se verifican en cada operación,
  no solo al mostrar el menú. Los cambios se serializan en una transacción para
  impedir carreras entre administradores. Los errores revierten la operación.
- La lista se filtra al escribir (con una pausa de 250 ms), también al borrar la búsqueda.
  Se puede consultar además al abrir el apartado, con Buscar o con los filtros.
  Las operaciones se ejecutan en segundo plano sin bloquear la interfaz.

## Clave temporal y primer acceso

- Crear una cuenta genera una clave aleatoria criptográfica de **8 dígitos**, incluidos
  posibles ceros iniciales. El administrador no la elige. Solo se almacena su hash Argon2.
- Tras confirmar la creación, un diálogo muestra usuario y clave una sola vez para
  entregarlos de forma privada. Al cerrarlo se limpia el campo; no hay consulta ni
  regeneración de esa clave desde Editar. Si se pierde, se usa la recuperación existente.
- Las cuentas nuevas se crean con `debe_cambiar_password=TRUE`. Autenticar con la clave
  temporal no crea una sesión ni registra acceso: abre exclusivamente el cambio obligatorio.
- El usuario debe elegir y confirmar una contraseña de 8 a 128 caracteres, distinta de
  la temporal. Solo después se abre el sistema. Cancelar vuelve al login sin conceder acceso.
- La autorización del cambio dura 10 minutos, es de un solo uso y se mantiene únicamente
  en memoria; no contiene una contraseña en claro. La BD revalida cuenta activa, marca
  pendiente y hash anterior en la misma actualización. Después la clave temporal deja de servir.
- Recuperar una cuenta mediante el flujo autorizado también establece una contraseña
  propia y elimina la obligación inicial. No habilita al administrador a elegir esa contraseña.
- Las cuentas existentes no cambian sus contraseñas ni quedan obligadas a cambiarlas.

## Contactos y preparación de recuperación

- Correo y teléfono son obligatorios al crear y al guardar una edición, tanto en el
  formulario como en el servicio. El correo permite recuperar la contraseña y el
  teléfono sirve como contacto. Se aceptan correos de cualquier proveedor, no solo Gmail.
  Las cuentas antiguas sin contactos siguen siendo consultables; al editarlas hay que completarlos.
- El correo se guarda en minúsculas, sin espacios exteriores, con formato validado.
  El teléfono se guarda en formato internacional: `+`, código de país y de 8 a 15 dígitos.
  Se aceptan espacios, guiones y paréntesis al escribir, que se eliminan al guardar.
- No se pueden compartir correos ni teléfonos entre cuentas, incluso inactivas.
  No se pueden vaciar ni omitir estos campos al guardar desde gestión de usuarios.
  Las columnas admiten NULL para conservar cuentas históricas sin inventar contactos.
- Registrar un contacto no lo marca como verificado. `correo_verificado_en` se
  actualiza al completar la recuperación por correo con código y aprobación.
  `telefono_verificado_en` no se modifica en este flujo. Cambiar un
  contacto invalida su verificación anterior; el formulario no permite editar estas marcas.
- La recuperación desde el login usa estos contactos, un código de un solo uso y la
  aprobación de otro administrador. **Los envíos están desactivados hasta configurar
  proveedores reales.** Ver [recuperación de contraseña](recuperacion_password.md).

## Foto y carnet de acceso

- La foto es opcional. Crear y editar permiten elegir, previsualizar, reemplazar o
  quitar una imagen. Sin foto, o si el archivo no está disponible, aparecen las iniciales.
- Se admiten JPG, PNG y WebP de hasta 10 MB y 25 megapíxeles. Al guardar se copia la
  imagen, se recorta al centro y se convierte a JPG de 512 × 512 píxeles.
- `foto_perfil VARCHAR(500)` almacena una ruta relativa como
  `assets/perfiles/<identificador>.jpg`. No guarda el archivo original ni datos binarios.
  Las copias no se versionan en Git. La selección cancelada no crea archivos; si falla
  la escritura en BD, se descarta la copia nueva. No se borran automáticamente fotos anteriores.
- Respaldar `assets/perfiles/` junto con la base. En instalaciones que comparten
  PostgreSQL, esta carpeta debe estar disponible en cada equipo (o sincronizada);
  compartir solo la base no comparte los archivos.
- El carnet muestra la foto en el frente y los contactos en el reverso. Pasar el mouse
  muestra temporalmente el reverso; un clic lo fija y otro vuelve al frente.

### Esquema de PostgreSQL

`database/flamar_postgres.sql` es la única definición de la tabla `usuarios`,
incluidos los contactos, sus restricciones y sus índices. Las pruebas de usuarios
también cargan ese archivo en un esquema aislado, sin duplicar su estructura.

Para actualizar una base existente se proporciona
`database/migrations/20261123_password_inicial.sql`: añade únicamente la marca
`debe_cambiar_password`, sin modificar contraseñas existentes. Es idempotente.
El esquema general sirve para crear una base nueva;
**no debe ejecutarse de nuevo sobre una base existente con datos**.

La aplicación de escritorio se conecta directamente a PostgreSQL con la configuración
existente. Estos controles pertenecen a la aplicación, no sustituyen permisos del
servidor frente a clientes modificados o acceso directo a las credenciales de PostgreSQL.
Desactivar una cuenta no cierra otras sesiones de escritorio que ya estén abiertas;
los permisos de gestión se revalidan al realizar cada operación.

## Pruebas

`python -B -m unittest discover -s tests -p "test_usuarios*.py"`

`python -B -m unittest tests.test_fotos_perfil`

`python -B -m unittest tests.test_primer_acceso`

Las pruebas PostgreSQL son optativas (`FLAMAR_TEST_DB=1`). Crean un esquema aislado
que siempre se revierte; no modifican cuentas reales.
