-- Aditiva e idempotente. Solo requiere el esquema base flamar_postgres.sql.
-- No modifica las tablas de los radares anteriores ni inserta datos de ejemplo.
BEGIN;
CREATE TABLE IF NOT EXISTS public.radar_lotes (
    id_lote BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    huella CHAR(64) NOT NULL UNIQUE,
    origen VARCHAR(40) NOT NULL,
    archivo TEXT,
    sha256 CHAR(64),
    metadata JSONB NOT NULL CHECK (jsonb_typeof(metadata) = 'object'),
    creado_por BIGINT NOT NULL REFERENCES public.usuarios(id_usuario),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS public.radar_senales (
    id_senal BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lote BIGINT NOT NULL REFERENCES public.radar_lotes(id_lote),
    clave_serie CHAR(64) NOT NULL,
    termino VARCHAR(200) NOT NULL,
    pais CHAR(2),
    observado_en TIMESTAMPTZ NOT NULL,
    valor DOUBLE PRECISION,
    datos JSONB NOT NULL CHECK (jsonb_typeof(datos) = 'object'),
    UNIQUE (id_lote, clave_serie, observado_en)
);
CREATE INDEX IF NOT EXISTS idx_radar_senales_serie_fecha
    ON public.radar_senales(clave_serie, observado_en DESC, id_senal DESC);
COMMIT;
