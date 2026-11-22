-- Migración aditiva. Ejecutar después de flamar_postgres.sql, una sola vez.
-- No altera productos, ventas, usuarios ni planes de abastecimiento.
BEGIN;

CREATE TABLE public.radar_temas (
    id_tema BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    termino VARCHAR(200) NOT NULL CHECK (length(trim(termino)) > 0),
    clave VARCHAR(200) NOT NULL UNIQUE,
    id_categoria BIGINT REFERENCES public.categorias(id_categoria),
    id_producto BIGINT REFERENCES public.productos(id_producto),
    imagen_path TEXT,
    creado_por BIGINT NOT NULL REFERENCES public.usuarios(id_usuario),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.radar_series (
    id_serie BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tema BIGINT NOT NULL REFERENCES public.radar_temas(id_tema),
    pais CHAR(2) NOT NULL CHECK (pais IN ('PE', 'US', 'MX', 'CL', 'CO', 'BR')),
    fuente VARCHAR(30) NOT NULL DEFAULT 'google_trends_csv' CHECK (fuente = 'google_trends_csv'),
    granularidad VARCHAR(10) NOT NULL CHECK (granularidad IN ('dia', 'semana', 'mes')),
    puntos JSONB NOT NULL CHECK (jsonb_typeof(puntos) = 'array' AND jsonb_array_length(puntos) BETWEEN 2 AND 2000),
    desde DATE NOT NULL,
    hasta DATE NOT NULL CHECK (hasta >= desde),
    archivo VARCHAR(255) NOT NULL,
    huella CHAR(64) NOT NULL,
    ultimo_parcial BOOLEAN NOT NULL,
    url TEXT NOT NULL,
    importado_por BIGINT NOT NULL REFERENCES public.usuarios(id_usuario),
    importado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_tema, pais, huella, ultimo_parcial)
);
CREATE INDEX idx_radar_series_tema_pais ON public.radar_series(id_tema, pais, hasta DESC, importado_en DESC);

CREATE TABLE public.radar_descubrimientos (
    id_descubrimiento BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    termino VARCHAR(200) NOT NULL,
    pais CHAR(2) NOT NULL CHECK (pais IN ('PE', 'US', 'MX', 'CL', 'CO', 'BR')),
    publicado TIMESTAMPTZ NOT NULL,
    trafico VARCHAR(50) NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    feed_url TEXT NOT NULL,
    noticias JSONB NOT NULL DEFAULT '[]'::JSONB CHECK (jsonb_typeof(noticias) = 'array'),
    consultado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pais, termino, publicado)
);
CREATE INDEX idx_radar_descubrimientos_fecha ON public.radar_descubrimientos(consultado_en DESC);

CREATE TABLE public.radar_evidencias (
    id_evidencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tema BIGINT NOT NULL REFERENCES public.radar_temas(id_tema),
    pais CHAR(2) NOT NULL CHECK (pais IN ('PE', 'US', 'MX', 'CL', 'CO', 'BR')),
    url TEXT NOT NULL,
    observado_el DATE NOT NULL,
    nota TEXT NOT NULL CHECK (length(trim(nota)) BETWEEN 1 AND 2000),
    fuente VARCHAR(30) NOT NULL DEFAULT 'tiktok_manual' CHECK (fuente = 'tiktok_manual'),
    registrado_por BIGINT NOT NULL REFERENCES public.usuarios(id_usuario),
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_tema, pais, url, observado_el)
);
COMMIT;
