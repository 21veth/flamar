BEGIN;

ALTER TABLE public.importaciones
    ADD COLUMN IF NOT EXISTS comparacion_eliminada BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE public.importaciones
SET comparacion_eliminada = FALSE
WHERE comparacion_eliminada IS NULL;

ALTER TABLE public.importaciones
    ALTER COLUMN comparacion_eliminada SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_importaciones_comparacion_pendiente
    ON public.importaciones (id_usuario)
    WHERE comparacion_eliminada = FALSE;

COMMIT;
