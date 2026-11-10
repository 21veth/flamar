BEGIN;

-- =====================================================
-- 1. USUARIOS
-- =====================================================
CREATE TABLE usuarios (
    id_usuario BIGINT GENERATED ALWAYS AS IDENTITY,
    usuario VARCHAR(100) NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso TIMESTAMPTZ,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_usuarios PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuarios_usuario UNIQUE (usuario),
    CONSTRAINT ck_usuarios_rol
        CHECK (rol IN ('administrador', 'gerente', 'trabajador'))
);

-- =====================================================
-- 2. CATEGORIAS
-- =====================================================
CREATE TABLE categorias (
    id_categoria BIGINT GENERATED ALWAYS AS IDENTITY,
    nombre VARCHAR(100) NOT NULL,

    CONSTRAINT pk_categorias PRIMARY KEY (id_categoria),
    CONSTRAINT uq_categorias_nombre UNIQUE (nombre)
);

-- =====================================================
-- 3. PRODUCTOS
-- =====================================================
CREATE TABLE productos (
    id_producto BIGINT GENERATED ALWAYS AS IDENTITY,
    codigo VARCHAR(30) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    id_categoria BIGINT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_productos PRIMARY KEY (id_producto),
    CONSTRAINT uq_productos_codigo UNIQUE (codigo),

    CONSTRAINT fk_productos_categoria
        FOREIGN KEY (id_categoria)
        REFERENCES categorias (id_categoria)
);

-- =====================================================
-- 4. IMPORTACIONES
-- =====================================================
CREATE TABLE importaciones (
    id_importacion BIGINT GENERATED ALWAYS AS IDENTITY,
    id_usuario BIGINT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    hash_archivo VARCHAR(64) NOT NULL,
    fecha_importacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    registros_totales INTEGER NOT NULL DEFAULT 0,
    registros_validos INTEGER NOT NULL DEFAULT 0,
    registros_rechazados INTEGER NOT NULL DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',

    CONSTRAINT pk_importaciones PRIMARY KEY (id_importacion),
    CONSTRAINT uq_importaciones_hash UNIQUE (hash_archivo),

    CONSTRAINT fk_importaciones_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario),

    CONSTRAINT ck_importaciones_conteos CHECK (
        registros_totales >= 0
        AND registros_validos >= 0
        AND registros_rechazados >= 0
        AND registros_validos + registros_rechazados
            <= registros_totales
    ),

    CONSTRAINT ck_importaciones_estado CHECK (
        estado IN ('pendiente', 'procesando', 'completada', 'fallida')
    ),

    CONSTRAINT ck_importaciones_completada CHECK (
        estado <> 'completada'
        OR registros_validos + registros_rechazados
            = registros_totales
    )
);

-- =====================================================
-- 5. ERRORES DE IMPORTACION
-- Una fila importada puede presentar varios errores.
-- =====================================================
CREATE TABLE errores_importacion (
    id_error BIGINT GENERATED ALWAYS AS IDENTITY,
    id_importacion BIGINT NOT NULL,
    numero_fila INTEGER NOT NULL,
    campo VARCHAR(100),
    valor_original TEXT,
    problema TEXT NOT NULL,

    CONSTRAINT pk_errores_importacion PRIMARY KEY (id_error),

    CONSTRAINT fk_errores_importacion_importacion
        FOREIGN KEY (id_importacion)
        REFERENCES importaciones (id_importacion),

    CONSTRAINT ck_errores_importacion_fila
        CHECK (numero_fila > 0)
);

-- =====================================================
-- 6. VENTAS
-- Una fila por ticket de la tienda.
-- =====================================================
CREATE TABLE ventas (
    id_venta BIGINT GENERATED ALWAYS AS IDENTITY,
    ticket VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    id_importacion BIGINT NOT NULL,

    CONSTRAINT pk_ventas PRIMARY KEY (id_venta),
    CONSTRAINT uq_ventas_ticket UNIQUE (ticket),

    CONSTRAINT fk_ventas_importacion
        FOREIGN KEY (id_importacion)
        REFERENCES importaciones (id_importacion)
);

-- =====================================================
-- 7. DETALLE DE VENTA
-- Una fila por linea de producto dentro del ticket.
-- Descuento: monto total descontado en esa linea.
-- =====================================================
CREATE TABLE detalle_venta (
    id_detalle BIGINT GENERATED ALWAYS AS IDENTITY,
    id_venta BIGINT NOT NULL,
    numero_linea INTEGER NOT NULL,
    id_producto BIGINT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL,
    descuento NUMERIC(12,2) NOT NULL DEFAULT 0,

    importe NUMERIC(14,2) GENERATED ALWAYS AS (
        cantidad * precio_unitario - descuento
    ) STORED,

    CONSTRAINT pk_detalle_venta PRIMARY KEY (id_detalle),

    CONSTRAINT fk_detalle_venta_venta
        FOREIGN KEY (id_venta)
        REFERENCES ventas (id_venta),

    CONSTRAINT fk_detalle_venta_producto
        FOREIGN KEY (id_producto)
        REFERENCES productos (id_producto),

    CONSTRAINT uq_detalle_venta_linea
        UNIQUE (id_venta, numero_linea),

    CONSTRAINT ck_detalle_venta_linea
        CHECK (numero_linea > 0),

    CONSTRAINT ck_detalle_venta_cantidad
        CHECK (cantidad > 0),

    CONSTRAINT ck_detalle_venta_precio
        CHECK (precio_unitario >= 0),

    CONSTRAINT ck_detalle_venta_descuento CHECK (
        descuento >= 0
        AND descuento <= cantidad * precio_unitario
    )
);

-- =====================================================
-- 8. MODELOS DE DEMANDA
-- =====================================================
CREATE TABLE modelos_demanda (
    id_modelo BIGINT GENERATED ALWAYS AS IDENTITY,
    nombre VARCHAR(100) NOT NULL,
    algoritmo VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    fecha_entrenamiento TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    datos_desde DATE NOT NULL,
    datos_hasta DATE NOT NULL,
    parametros JSONB NOT NULL DEFAULT '{}'::JSONB,
    metricas_evaluacion JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT pk_modelos_demanda PRIMARY KEY (id_modelo),

    CONSTRAINT uq_modelos_demanda_version
        UNIQUE (nombre, version),

    CONSTRAINT ck_modelos_demanda_fechas
        CHECK (datos_hasta >= datos_desde),

    CONSTRAINT ck_modelos_demanda_parametros
        CHECK (jsonb_typeof(parametros) = 'object'),

    CONSTRAINT ck_modelos_demanda_metricas
        CHECK (jsonb_typeof(metricas_evaluacion) = 'object')
);

-- =====================================================
-- 9. PREDICCIONES DE DEMANDA
-- Cantidad estimada para todo el periodo indicado.
-- =====================================================
CREATE TABLE predicciones_demanda (
    id_prediccion BIGINT GENERATED ALWAYS AS IDENTITY,
    id_producto BIGINT NOT NULL,
    id_modelo BIGINT NOT NULL,
    periodo_inicio DATE NOT NULL,
    periodo_fin DATE NOT NULL,
    cantidad_estimada NUMERIC(12,2) NOT NULL,
    fecha_generacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_predicciones_demanda PRIMARY KEY (id_prediccion),

    CONSTRAINT fk_predicciones_demanda_producto
        FOREIGN KEY (id_producto)
        REFERENCES productos (id_producto),

    CONSTRAINT fk_predicciones_demanda_modelo
        FOREIGN KEY (id_modelo)
        REFERENCES modelos_demanda (id_modelo),

    CONSTRAINT ck_predicciones_demanda_periodo
        CHECK (periodo_fin >= periodo_inicio),

    CONSTRAINT ck_predicciones_demanda_cantidad
        CHECK (cantidad_estimada >= 0)
);

-- =====================================================
-- 10. PLANES DE ABASTECIMIENTO
-- Cada registro planifica el producto de una prediccion.
-- Las existencias son una referencia, no un inventario.
-- =====================================================
CREATE TABLE planes_abastecimiento (
    id_plan BIGINT GENERATED ALWAYS AS IDENTITY,
    id_usuario BIGINT NOT NULL,
    id_prediccion BIGINT NOT NULL,
    fecha_planificacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_referencia_existencias DATE,
    existencias_disponibles INTEGER,
    unidades_pendientes INTEGER,
    plazo_entrega_dias INTEGER,
    cantidad_sugerida INTEGER,
    criterio_calculo TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',

    CONSTRAINT pk_planes_abastecimiento PRIMARY KEY (id_plan),

    CONSTRAINT fk_planes_abastecimiento_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario),

    CONSTRAINT fk_planes_abastecimiento_prediccion
        FOREIGN KEY (id_prediccion)
        REFERENCES predicciones_demanda (id_prediccion),

    CONSTRAINT ck_planes_abastecimiento_existencias
        CHECK (existencias_disponibles >= 0),

    CONSTRAINT ck_planes_abastecimiento_pendientes
        CHECK (unidades_pendientes >= 0),

    CONSTRAINT ck_planes_abastecimiento_plazo
        CHECK (plazo_entrega_dias >= 0),

    CONSTRAINT ck_planes_abastecimiento_cantidad
        CHECK (cantidad_sugerida >= 0),

    CONSTRAINT ck_planes_abastecimiento_estado
        CHECK (estado IN ('borrador', 'revisado', 'aprobado')),

    CONSTRAINT ck_planes_abastecimiento_datos CHECK (
        cantidad_sugerida IS NULL
        OR (
            fecha_referencia_existencias IS NOT NULL
            AND existencias_disponibles IS NOT NULL
            AND unidades_pendientes IS NOT NULL
            AND plazo_entrega_dias IS NOT NULL
            AND criterio_calculo IS NOT NULL
            AND LENGTH(TRIM(criterio_calculo)) > 0
        )
    ),

    CONSTRAINT ck_planes_abastecimiento_aprobacion CHECK (
        estado <> 'aprobado'
        OR cantidad_sugerida IS NOT NULL
    )
);

-- =====================================================
-- INDICES PARA CONSULTAS Y RELACIONES
-- Las PRIMARY KEY y UNIQUE ya crean sus propios indices.
-- =====================================================
CREATE INDEX idx_productos_categoria
    ON productos (id_categoria);

CREATE INDEX idx_importaciones_usuario
    ON importaciones (id_usuario);

CREATE INDEX idx_errores_importacion_archivo
    ON errores_importacion (id_importacion);

CREATE INDEX idx_ventas_fecha
    ON ventas (fecha);

CREATE INDEX idx_ventas_importacion
    ON ventas (id_importacion);

CREATE INDEX idx_detalle_venta_producto
    ON detalle_venta (id_producto);

CREATE INDEX idx_predicciones_producto_periodo
    ON predicciones_demanda (
        id_producto, periodo_inicio, periodo_fin
    );

CREATE INDEX idx_predicciones_modelo
    ON predicciones_demanda (id_modelo);

CREATE INDEX idx_planes_usuario
    ON planes_abastecimiento (id_usuario);

CREATE INDEX idx_planes_prediccion
    ON planes_abastecimiento (id_prediccion);

-- =====================================================
-- VISTA: TOTAL DE CADA TICKET
-- Se obtiene sumando los importes de sus productos.
-- =====================================================
CREATE VIEW totales_ventas AS
SELECT
    v.id_venta,
    v.ticket,
    v.fecha,
    v.hora,
    v.metodo_pago,
    SUM(d.importe) AS total
FROM ventas AS v
INNER JOIN detalle_venta AS d
    ON d.id_venta = v.id_venta
GROUP BY
    v.id_venta,
    v.ticket,
    v.fecha,
    v.hora,
    v.metodo_pago;

COMMIT;