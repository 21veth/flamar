BEGIN;

ALTER TABLE public.comparaciones
    ADD COLUMN IF NOT EXISTS proveedor_recomendado_nombre VARCHAR(255);

ALTER TABLE public.detalle_comparacion
    ADD COLUMN IF NOT EXISTS proveedor_nombre VARCHAR(255),
    ADD COLUMN IF NOT EXISTS producto_codigo VARCHAR(30),
    ADD COLUMN IF NOT EXISTS producto_nombre VARCHAR(150),
    ADD COLUMN IF NOT EXISTS categoria_nombre VARCHAR(100);

COMMIT;
