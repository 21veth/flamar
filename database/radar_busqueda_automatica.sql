-- Radar simplificado. Solo requiere el esquema base existente (usuarios).
-- No requiere las tablas del anterior flujo manual ni las modifica.
BEGIN;
CREATE TABLE IF NOT EXISTS public.radar_busquedas (
    id_busqueda BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resultado JSONB NOT NULL CHECK (jsonb_typeof(resultado) = 'object'),
    creado_por BIGINT NOT NULL REFERENCES public.usuarios(id_usuario),
    guardado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
