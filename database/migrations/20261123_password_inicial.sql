-- Ejecutar una vez sobre una base existente antes de usar esta versión.
-- No cambia contraseñas ni obliga a las cuentas existentes a cambiarlas.
BEGIN;
ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS debe_cambiar_password BOOLEAN NOT NULL DEFAULT FALSE;
COMMIT;
