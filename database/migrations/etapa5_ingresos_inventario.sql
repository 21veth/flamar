BEGIN;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS unidad_medida VARCHAR(30),
    ADD COLUMN IF NOT EXISTS stock_minimo INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS precio_venta_actual NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS fecha_ultimo_precio_venta DATE,
    ADD COLUMN IF NOT EXISTS fecha_ultimo_stock_minimo DATE;

UPDATE productos SET stock_minimo = 0 WHERE stock_minimo IS NULL;
UPDATE productos SET precio_venta_actual = 0 WHERE precio_venta_actual IS NULL;

ALTER TABLE productos ALTER COLUMN stock_minimo SET NOT NULL;
ALTER TABLE productos ALTER COLUMN precio_venta_actual SET NOT NULL;

ALTER TABLE productos DROP CONSTRAINT IF EXISTS ck_productos_stock_minimo;
ALTER TABLE productos ADD CONSTRAINT ck_productos_stock_minimo
    CHECK (stock_minimo >= 0);

ALTER TABLE productos DROP CONSTRAINT IF EXISTS ck_productos_precio_venta;
ALTER TABLE productos ADD CONSTRAINT ck_productos_precio_venta
    CHECK (precio_venta_actual >= 0);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'detalle_ingreso_inventario'
          AND column_name = 'cantidad_ingresada'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'detalle_ingreso_inventario'
          AND column_name = 'cantidad'
    ) THEN
        ALTER TABLE public.detalle_ingreso_inventario
            RENAME COLUMN cantidad_ingresada TO cantidad;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'detalle_ingreso_inventario'
          AND column_name = 'precio_venta_archivo'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'detalle_ingreso_inventario'
          AND column_name = 'precio_venta'
    ) THEN
        ALTER TABLE public.detalle_ingreso_inventario
            RENAME COLUMN precio_venta_archivo TO precio_venta;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ingresos_inventario (
    id_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    id_importacion BIGINT NOT NULL,
    id_proveedor BIGINT NOT NULL,
    id_comparacion BIGINT,
    fecha_ingreso DATE NOT NULL,
    numero_productos INTEGER NOT NULL DEFAULT 0,
    total_unidades INTEGER NOT NULL DEFAULT 0,
    observacion TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE ingresos_inventario
    ADD COLUMN IF NOT EXISTS id_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    ADD COLUMN IF NOT EXISTS id_importacion BIGINT NOT NULL,
    ADD COLUMN IF NOT EXISTS id_proveedor BIGINT NOT NULL,
    ADD COLUMN IF NOT EXISTS id_comparacion BIGINT,
    ADD COLUMN IF NOT EXISTS fecha_ingreso DATE NOT NULL,
    ADD COLUMN IF NOT EXISTS numero_productos INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_unidades INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS observacion TEXT,
    ADD COLUMN IF NOT EXISTS creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

DO $$
DECLARE
    nombre_constraint TEXT;
BEGIN
    SELECT conname INTO nombre_constraint
    FROM pg_constraint
    WHERE conrelid = 'public.ingresos_inventario'::regclass
      AND contype = 'p'
    LIMIT 1;

    IF nombre_constraint IS NULL THEN
        ALTER TABLE ingresos_inventario ADD CONSTRAINT pk_ingresos_inventario
            PRIMARY KEY (id_ingreso);
    ELSIF nombre_constraint <> 'pk_ingresos_inventario' THEN
        EXECUTE format(
            'ALTER TABLE public.ingresos_inventario RENAME CONSTRAINT %I TO pk_ingresos_inventario',
            nombre_constraint
        );
    END IF;
END $$;

ALTER TABLE ingresos_inventario DROP CONSTRAINT IF EXISTS fk_ingresos_inventario_importacion;
ALTER TABLE ingresos_inventario ADD CONSTRAINT fk_ingresos_inventario_importacion
    FOREIGN KEY (id_importacion) REFERENCES importaciones (id_importacion);

ALTER TABLE ingresos_inventario DROP CONSTRAINT IF EXISTS fk_ingresos_inventario_proveedor;
ALTER TABLE ingresos_inventario ADD CONSTRAINT fk_ingresos_inventario_proveedor
    FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor);

ALTER TABLE ingresos_inventario DROP CONSTRAINT IF EXISTS fk_ingresos_inventario_comparacion;
ALTER TABLE ingresos_inventario ADD CONSTRAINT fk_ingresos_inventario_comparacion
    FOREIGN KEY (id_comparacion) REFERENCES comparaciones (id_comparacion);

ALTER TABLE ingresos_inventario DROP CONSTRAINT IF EXISTS ck_ingresos_inventario_numero_productos;
ALTER TABLE ingresos_inventario ADD CONSTRAINT ck_ingresos_inventario_numero_productos
    CHECK (numero_productos >= 0);

ALTER TABLE ingresos_inventario DROP CONSTRAINT IF EXISTS ck_ingresos_inventario_total_unidades;
ALTER TABLE ingresos_inventario ADD CONSTRAINT ck_ingresos_inventario_total_unidades
    CHECK (total_unidades >= 0);

CREATE TABLE IF NOT EXISTS detalle_ingreso_inventario (
    id_detalle_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    id_ingreso BIGINT NOT NULL,
    id_producto BIGINT NOT NULL,
    numero_fila_excel INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    precio_compra NUMERIC(12,2) NOT NULL,
    precio_venta NUMERIC(12,2) NOT NULL,
    unidad_medida VARCHAR(30),
    fecha_ingreso DATE NOT NULL
);

ALTER TABLE detalle_ingreso_inventario
    ADD COLUMN IF NOT EXISTS id_detalle_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    ADD COLUMN IF NOT EXISTS id_ingreso BIGINT NOT NULL,
    ADD COLUMN IF NOT EXISTS id_producto BIGINT NOT NULL,
    ADD COLUMN IF NOT EXISTS numero_fila_excel INTEGER NOT NULL,
    ADD COLUMN IF NOT EXISTS cantidad INTEGER NOT NULL,
    ADD COLUMN IF NOT EXISTS stock_minimo INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS precio_compra NUMERIC(12,2) NOT NULL,
    ADD COLUMN IF NOT EXISTS precio_venta NUMERIC(12,2) NOT NULL,
    ADD COLUMN IF NOT EXISTS unidad_medida VARCHAR(30),
    ADD COLUMN IF NOT EXISTS fecha_ingreso DATE NOT NULL;

DO $$
DECLARE
    nombre_constraint TEXT;
BEGIN
    SELECT conname INTO nombre_constraint
    FROM pg_constraint
    WHERE conrelid = 'public.detalle_ingreso_inventario'::regclass
      AND contype = 'p'
    LIMIT 1;

    IF nombre_constraint IS NULL THEN
        ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT pk_detalle_ingreso_inventario
            PRIMARY KEY (id_detalle_ingreso);
    ELSIF nombre_constraint <> 'pk_detalle_ingreso_inventario' THEN
        EXECUTE format(
            'ALTER TABLE public.detalle_ingreso_inventario RENAME CONSTRAINT %I TO pk_detalle_ingreso_inventario',
            nombre_constraint
        );
    END IF;
END $$;

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS uq_detalle_ingreso_fila;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT uq_detalle_ingreso_fila
    UNIQUE (id_ingreso, numero_fila_excel);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS fk_detalle_ingreso_ingreso;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT fk_detalle_ingreso_ingreso
    FOREIGN KEY (id_ingreso) REFERENCES ingresos_inventario (id_ingreso);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS fk_detalle_ingreso_producto;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT fk_detalle_ingreso_producto
    FOREIGN KEY (id_producto) REFERENCES productos (id_producto);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS ck_detalle_ingreso_fila;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT ck_detalle_ingreso_fila
    CHECK (numero_fila_excel > 0);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS ck_detalle_ingreso_cantidad;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT ck_detalle_ingreso_cantidad
    CHECK (cantidad > 0);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS ck_detalle_ingreso_stock_minimo;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT ck_detalle_ingreso_stock_minimo
    CHECK (stock_minimo >= 0);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS ck_detalle_ingreso_precio_compra;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT ck_detalle_ingreso_precio_compra
    CHECK (precio_compra > 0);

ALTER TABLE detalle_ingreso_inventario DROP CONSTRAINT IF EXISTS ck_detalle_ingreso_precio_venta;
ALTER TABLE detalle_ingreso_inventario ADD CONSTRAINT ck_detalle_ingreso_precio_venta
    CHECK (precio_venta > 0);

CREATE INDEX IF NOT EXISTS idx_importaciones_hash
    ON importaciones (hash_archivo);

CREATE INDEX IF NOT EXISTS idx_ingresos_inventario_proveedor
    ON ingresos_inventario (id_proveedor);

CREATE INDEX IF NOT EXISTS idx_ingresos_inventario_fecha
    ON ingresos_inventario (fecha_ingreso);

CREATE INDEX IF NOT EXISTS idx_detalle_ingreso_producto
    ON detalle_ingreso_inventario (id_producto);

CREATE INDEX IF NOT EXISTS idx_detalle_ingreso_fecha
    ON detalle_ingreso_inventario (fecha_ingreso);

SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      (table_name = 'productos' AND column_name IN (
          'unidad_medida', 'stock_minimo', 'precio_venta_actual',
          'fecha_ultimo_precio_venta', 'fecha_ultimo_stock_minimo'
      ))
      OR table_name IN ('ingresos_inventario', 'detalle_ingreso_inventario')
  )
ORDER BY table_name, ordinal_position;

COMMIT;
