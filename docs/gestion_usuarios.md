# Gestión de usuarios

Disponible al final de la navegación, después de Reportes y antes de Cerrar sesión,
únicamente para sesiones de administrador. Usa la tabla existente `public.usuarios`.
No incluye cuentas ni contraseñas de ejemplo. La definición de usuarios y sus campos
de contacto se mantiene únicamente en `database/flamar_postgres.sql`.

- Listar y buscar por usuario, correo o teléfono, filtrar por rol y estado, crear, modificar y eliminar.
- Roles disponibles: administrador, gerente y trabajador.
- El módulo reúne dos pestañas: **Usuarios** y **Solicitudes de contraseña**.
  Las aprobaciones y rechazos se gestionan en la segunda, con contador de pendientes.
- Contraseñas de 6 a 128 caracteres, almacenadas con Argon2, compatibles con el login.
  Al editar, una contraseña vacía conserva la anterior. No se muestran ni devuelven hashes.
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

## Contactos y preparación de recuperación

- Correo y teléfono son opcionales para conservar las cuentas existentes sin inventar datos.
  Se añaden al crear o editar un usuario, y se muestran en su ficha lateral.
- El correo se guarda en minúsculas, sin espacios exteriores, con formato validado.
  El teléfono se guarda en formato internacional: `+`, código de país y de 8 a 15 dígitos.
  Se aceptan espacios, guiones y paréntesis al escribir, que se eliminan al guardar.
- No se pueden compartir correos ni teléfonos entre cuentas, incluso inactivas.
  Los valores vacíos se almacenan como NULL; varios usuarios pueden no tener contactos.
- Al editar, dejar el campo vacío elimina ese contacto. Si un cliente antiguo omite
  el campo, se conserva el valor existente.
- Registrar un contacto no lo marca como verificado. `correo_verificado_en` se
  actualiza al completar la recuperación por correo con código y aprobación.
  `telefono_verificado_en` no se modifica en este flujo. Cambiar o eliminar un
  contacto invalida su verificación anterior; el formulario no permite editar estas marcas.
- La recuperación desde el login usa estos contactos, un código de un solo uso y la
  aprobación de otro administrador. **Los envíos están desactivados hasta configurar
  proveedores reales.** Ver [recuperación de contraseña](recuperacion_password.md).

### Esquema de PostgreSQL

`database/flamar_postgres.sql` es la única definición de la tabla `usuarios`,
incluidos los contactos, sus restricciones y sus índices. Las pruebas de usuarios
también cargan ese archivo en un esquema aislado, sin duplicar su estructura.

La base configurada ya contiene estos campos y no necesita ejecutar ningún archivo
adicional para esta funcionalidad. El esquema general sirve para crear una base
nueva; **no debe ejecutarse de nuevo sobre una base existente con datos**.

La aplicación de escritorio se conecta directamente a PostgreSQL con la configuración
existente. Estos controles pertenecen a la aplicación, no sustituyen permisos del
servidor frente a clientes modificados o acceso directo a las credenciales de PostgreSQL.
Desactivar una cuenta no cierra otras sesiones de escritorio que ya estén abiertas;
los permisos de gestión se revalidan al realizar cada operación.

## Pruebas

`python -B -m unittest discover -s tests -p "test_usuarios*.py"`

Las pruebas PostgreSQL son optativas (`FLAMAR_TEST_DB=1`). Crean un esquema aislado
que siempre se revierte; no modifican cuentas reales.
