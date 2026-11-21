-- =====================================================
-- Etapa 2/5 - Validacion y resultados de cotizaciones de proveedores
--
-- Ejecutar antes de usar la Etapa 5. No crea tablas nuevas.
--
-- Cambios:
--   1. Quitar la unicidad de hash_archivo para permitir
--      registrar un nuevo intento tras una importacion fallida.
--   2. Ampliar los estados permitidos para distinguir un
--      archivo valido de uno con errores.
-- =====================================================

ALTER TABLE importaciones
    DROP CONSTRAINT IF EXISTS uq_importaciones_hash;

CREATE INDEX IF NOT EXISTS idx_importaciones_hash
    ON importaciones (hash_archivo);

ALTER TABLE importaciones
    DROP CONSTRAINT IF EXISTS ck_importaciones_estado;

ALTER TABLE importaciones
    ADD CONSTRAINT ck_importaciones_estado CHECK (
        estado IN (
            'pendiente', 'validado', 'con_errores',
            'procesando', 'completada', 'fallida'
        )
    );
