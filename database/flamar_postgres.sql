BEGIN;

-- =====================================================
-- 1. USUARIOS
-- =====================================================
CREATE TABLE usuarios (
    id_usuario BIGINT GENERATED ALWAYS AS IDENTITY,
    usuario VARCHAR(100) NOT NULL,
    password_hash TEXT NOT NULL,
    debe_cambiar_password BOOLEAN NOT NULL DEFAULT FALSE,
    rol VARCHAR(20) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso TIMESTAMPTZ,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    correo VARCHAR(254),
    telefono VARCHAR(16),
    foto_perfil VARCHAR(500),
    correo_verificado_en TIMESTAMPTZ,
    telefono_verificado_en TIMESTAMPTZ,

    CONSTRAINT pk_usuarios PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuarios_usuario UNIQUE (usuario),
    CONSTRAINT ck_usuarios_rol
        CHECK (rol IN ('administrador', 'gerente', 'trabajador')),
    CONSTRAINT ck_usuarios_correo CHECK (
        correo IS NULL OR (
            correo = lower(btrim(correo))
            AND correo ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        )
    ),
    CONSTRAINT ck_usuarios_telefono
        CHECK (telefono IS NULL OR telefono ~ '^\+[1-9][0-9]{7,14}$'),
    CONSTRAINT ck_usuarios_contacto_verificado CHECK (
        (correo_verificado_en IS NULL OR correo IS NOT NULL)
        AND (telefono_verificado_en IS NULL OR telefono IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_usuarios_correo ON usuarios (lower(correo)) WHERE correo IS NOT NULL;
CREATE UNIQUE INDEX uq_usuarios_telefono ON usuarios (telefono) WHERE telefono IS NOT NULL;

-- INICIO RECUPERACION DE CONTRASENA
-- Una solicitud guarda pruebas y aprobación, nunca códigos ni contraseñas en texto plano.
CREATE TABLE recuperaciones_password (
    id_solicitud UUID PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuarios (id_usuario),
    -- Solo se crean recuperaciones por correo; el otro valor permite conservar históricos.
    canal VARCHAR(10) NOT NULL CHECK (canal IN ('correo', 'whatsapp')),
    -- Vacío mientras una solicitud pendiente espera que el administrador registre el correo.
    destino VARCHAR(254) NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    codigo_hash CHAR(64),
    password_firma CHAR(64) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN (
        'enviando', 'codigo_enviado', 'pendiente', 'aprobada', 'rechazada',
        'completada', 'expirada', 'bloqueada', 'envio_fallido', 'cancelada'
    )),
    intentos SMALLINT NOT NULL DEFAULT 0 CHECK (intentos BETWEEN 0 AND 5),
    solicitado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    codigo_caduca_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '3 hours',
    caduca_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '3 hours',
    verificado_en TIMESTAMPTZ,
    id_administrador BIGINT REFERENCES usuarios (id_usuario),
    resuelto_en TIMESTAMPTZ,
    aprobacion_caduca_en TIMESTAMPTZ,
    cambiado_en TIMESTAMPTZ,
    envio_error VARCHAR(40),
    envio_intentado_en TIMESTAMPTZ,
    envio_intentos SMALLINT NOT NULL DEFAULT 0,
    CONSTRAINT ck_recuperacion_envio_intentos CHECK (envio_intentos BETWEEN 0 AND 3),
    CONSTRAINT ck_recuperacion_otro_administrador CHECK (
        id_administrador IS NULL OR id_administrador <> id_usuario
    ),
    CONSTRAINT ck_recuperacion_aprobacion CHECK (
        estado NOT IN ('aprobada', 'completada') OR (
            verificado_en IS NOT NULL AND id_administrador IS NOT NULL
            AND resuelto_en IS NOT NULL AND aprobacion_caduca_en IS NOT NULL
        )
    ),
    CONSTRAINT ck_recuperacion_autorizacion_codigo CHECK (
        estado NOT IN ('enviando', 'codigo_enviado') OR (
            id_administrador IS NOT NULL AND resuelto_en IS NOT NULL
            AND aprobacion_caduca_en IS NOT NULL
        )
    )
);
CREATE INDEX ix_recuperacion_usuario_fecha ON recuperaciones_password (id_usuario, solicitado_en DESC);
CREATE INDEX ix_recuperacion_estado_fecha ON recuperaciones_password (estado, solicitado_en DESC);
-- FIN RECUPERACION DE CONTRASENA

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
    marca VARCHAR(100),
    presentacion VARCHAR(100),
    unidad_medida VARCHAR(30),
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    precio_venta_actual NUMERIC(12,2) NOT NULL DEFAULT 0,
    fecha_ultimo_precio_venta DATE,
    fecha_ultimo_stock_minimo DATE,

    CONSTRAINT pk_productos PRIMARY KEY (id_producto),
    CONSTRAINT uq_productos_codigo UNIQUE (codigo),

    CONSTRAINT ck_productos_stock_minimo CHECK (stock_minimo >= 0),
    CONSTRAINT ck_productos_precio_venta CHECK (precio_venta_actual >= 0),

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
    comparacion_eliminada BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_importaciones PRIMARY KEY (id_importacion),

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
        estado IN (
            'pendiente', 'validado', 'con_errores',
            'procesando', 'completada', 'fallida'
        )
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
-- 11. PROVEEDORES
-- =====================================================
CREATE TABLE proveedores (
    id_proveedor BIGINT GENERATED ALWAYS AS IDENTITY,
    nombre VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_proveedores PRIMARY KEY (id_proveedor),
    CONSTRAINT proveedores_nombre_key UNIQUE (nombre)
);

-- =====================================================
-- 12. COTIZACIONES
-- Una cotizacion por archivo importado.
-- =====================================================
CREATE TABLE cotizaciones (
    id_cotizacion BIGINT GENERATED ALWAYS AS IDENTITY,
    id_proveedor BIGINT NOT NULL,
    id_importacion BIGINT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'vigente',

    CONSTRAINT pk_cotizaciones PRIMARY KEY (id_cotizacion),
    CONSTRAINT cotizaciones_id_importacion_key UNIQUE (id_importacion),

    CONSTRAINT fk_cotizaciones_proveedor
        FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor),
    CONSTRAINT fk_cotizaciones_importacion
        FOREIGN KEY (id_importacion) REFERENCES importaciones (id_importacion),

    CONSTRAINT ck_cotizaciones_estado
        CHECK (estado IN ('vigente', 'reemplazada'))
);

-- =====================================================
-- 13. DETALLE DE COTIZACION
-- Una oferta por producto dentro de una cotizacion.
-- descuento_porcentaje se expresa como fraccion (0 a 1).
-- =====================================================
CREATE TABLE detalle_cotizacion (
    id_detalle_cotizacion BIGINT GENERATED ALWAYS AS IDENTITY,
    id_cotizacion BIGINT NOT NULL,
    id_producto BIGINT NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL,
    stock_disponible INTEGER NOT NULL,
    compra_minima INTEGER NOT NULL,
    descuento_desde INTEGER,
    descuento_porcentaje NUMERIC(5,4) NOT NULL DEFAULT 0,
    entrega_dias INTEGER NOT NULL,

    CONSTRAINT pk_detalle_cotizacion PRIMARY KEY (id_detalle_cotizacion),
    CONSTRAINT uq_detalle_cotizacion_producto
        UNIQUE (id_cotizacion, id_producto),

    CONSTRAINT fk_detalle_cotizacion_cotizacion
        FOREIGN KEY (id_cotizacion) REFERENCES cotizaciones (id_cotizacion),
    CONSTRAINT fk_detalle_cotizacion_producto
        FOREIGN KEY (id_producto) REFERENCES productos (id_producto),

    CONSTRAINT ck_detalle_cotizacion_precio CHECK (precio_unitario >= 0),
    CONSTRAINT ck_detalle_cotizacion_stock CHECK (stock_disponible >= 0),
    CONSTRAINT ck_detalle_cotizacion_compra_minima CHECK (compra_minima > 0),
    CONSTRAINT ck_detalle_cotizacion_descuento_desde CHECK (descuento_desde IS NULL OR descuento_desde > 0),
    CONSTRAINT ck_detalle_cotizacion_descuento_porcentaje
        CHECK (descuento_porcentaje >= 0 AND descuento_porcentaje <= 1),
    CONSTRAINT ck_detalle_cotizacion_entrega CHECK (entrega_dias >= 0)
);

-- =====================================================
-- 14. COMPARACIONES
-- =====================================================
CREATE TABLE comparaciones (
    id_comparacion BIGINT GENERATED ALWAYS AS IDENTITY,
    nombre VARCHAR(150) NOT NULL,
    tipo_productos VARCHAR(100),
    id_usuario BIGINT NOT NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    id_proveedor_recomendado BIGINT,
    costo_proveedor_recomendado NUMERIC(14,2),
    costo_compra_combinada NUMERIC(14,2),
    costo_referencia NUMERIC(14,2),
    ahorro_estimado NUMERIC(14,2),
    justificacion TEXT,
    proveedor_recomendado_nombre VARCHAR(255),

    CONSTRAINT pk_comparaciones PRIMARY KEY (id_comparacion),

    CONSTRAINT fk_comparaciones_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario),
    CONSTRAINT fk_comparaciones_proveedor_recomendado
        FOREIGN KEY (id_proveedor_recomendado) REFERENCES proveedores (id_proveedor),

    CONSTRAINT ck_comparaciones_estado
        CHECK (estado IN ('borrador', 'completada')),
    CONSTRAINT ck_comparaciones_costo_proveedor CHECK (costo_proveedor_recomendado >= 0),
    CONSTRAINT ck_comparaciones_costo_combinado CHECK (costo_compra_combinada >= 0),
    CONSTRAINT ck_comparaciones_costo_referencia CHECK (costo_referencia >= 0)
);

-- =====================================================
-- 15. DETALLE DE COMPARACION
-- Una fila por oferta evaluada dentro de una comparacion.
-- =====================================================
CREATE TABLE detalle_comparacion (
    id_detalle_comparacion BIGINT GENERATED ALWAYS AS IDENTITY,
    id_comparacion BIGINT NOT NULL,
    id_detalle_cotizacion BIGINT NOT NULL,
    cantidad_requerida INTEGER NOT NULL,
    precio_evaluado NUMERIC(12,2),
    costo_total_linea NUMERIC(14,2),
    oferta_valida BOOLEAN NOT NULL DEFAULT TRUE,
    seleccionado_combinada BOOLEAN NOT NULL DEFAULT FALSE,
    observacion TEXT,
    proveedor_nombre VARCHAR(255),
    producto_codigo VARCHAR(30),
    producto_nombre VARCHAR(150),
    categoria_nombre VARCHAR(100),

    CONSTRAINT pk_detalle_comparacion PRIMARY KEY (id_detalle_comparacion),
    CONSTRAINT uq_detalle_comparacion_oferta
        UNIQUE (id_comparacion, id_detalle_cotizacion),

    CONSTRAINT fk_detalle_comparacion_comparacion
        FOREIGN KEY (id_comparacion) REFERENCES comparaciones (id_comparacion),
    CONSTRAINT fk_detalle_comparacion_oferta
        FOREIGN KEY (id_detalle_cotizacion)
        REFERENCES detalle_cotizacion (id_detalle_cotizacion),

    CONSTRAINT ck_detalle_comparacion_cantidad CHECK (cantidad_requerida > 0),
    CONSTRAINT ck_detalle_comparacion_precio CHECK (precio_evaluado >= 0),
    CONSTRAINT ck_detalle_comparacion_total CHECK (costo_total_linea >= 0),
    CONSTRAINT ck_detalle_comparacion_seleccion
        CHECK (NOT seleccionado_combinada OR oferta_valida)
);

CREATE TABLE ingresos_inventario (
    id_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    id_importacion BIGINT NOT NULL,
    id_proveedor BIGINT NOT NULL,
    id_comparacion BIGINT,
    fecha_ingreso DATE NOT NULL,
    numero_productos INTEGER NOT NULL DEFAULT 0,
    total_unidades INTEGER NOT NULL DEFAULT 0,
    observacion TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_ingresos_inventario PRIMARY KEY (id_ingreso),

    CONSTRAINT fk_ingresos_inventario_importacion
        FOREIGN KEY (id_importacion) REFERENCES importaciones (id_importacion),
    CONSTRAINT fk_ingresos_inventario_proveedor
        FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor),
    CONSTRAINT fk_ingresos_inventario_comparacion
        FOREIGN KEY (id_comparacion) REFERENCES comparaciones (id_comparacion),

    CONSTRAINT ck_ingresos_inventario_numero_productos CHECK (numero_productos >= 0),
    CONSTRAINT ck_ingresos_inventario_total_unidades CHECK (total_unidades >= 0)
);

CREATE TABLE detalle_ingreso_inventario (
    id_detalle_ingreso BIGINT GENERATED ALWAYS AS IDENTITY,
    id_ingreso BIGINT NOT NULL,
    id_producto BIGINT NOT NULL,
    numero_fila_excel INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    precio_compra NUMERIC(12,2) NOT NULL,
    precio_venta NUMERIC(12,2) NOT NULL,
    unidad_medida VARCHAR(30),
    fecha_ingreso DATE NOT NULL,

    CONSTRAINT pk_detalle_ingreso_inventario PRIMARY KEY (id_detalle_ingreso),
    CONSTRAINT uq_detalle_ingreso_fila UNIQUE (id_ingreso, numero_fila_excel),

    CONSTRAINT fk_detalle_ingreso_ingreso
        FOREIGN KEY (id_ingreso) REFERENCES ingresos_inventario (id_ingreso),
    CONSTRAINT fk_detalle_ingreso_producto
        FOREIGN KEY (id_producto) REFERENCES productos (id_producto),

    CONSTRAINT ck_detalle_ingreso_fila CHECK (numero_fila_excel > 0),
    CONSTRAINT ck_detalle_ingreso_cantidad CHECK (cantidad > 0),
    CONSTRAINT ck_detalle_ingreso_stock_minimo CHECK (stock_minimo >= 0),
    CONSTRAINT ck_detalle_ingreso_precio_compra CHECK (precio_compra > 0),
    CONSTRAINT ck_detalle_ingreso_precio_venta CHECK (precio_venta > 0)
);

-- =====================================================
-- INDICES PARA CONSULTAS Y RELACIONES
-- Las PRIMARY KEY y UNIQUE ya crean sus propios indices.
-- =====================================================
CREATE INDEX idx_productos_categoria
    ON productos (id_categoria);

CREATE INDEX idx_importaciones_usuario
    ON importaciones (id_usuario);

CREATE INDEX idx_importaciones_hash
    ON importaciones (hash_archivo);

CREATE INDEX idx_importaciones_comparacion_pendiente
    ON importaciones (id_usuario)
    WHERE comparacion_eliminada = FALSE;

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

CREATE INDEX idx_cotizaciones_proveedor
    ON cotizaciones (id_proveedor);

CREATE INDEX idx_detalle_cotizacion_producto
    ON detalle_cotizacion (id_producto);

CREATE INDEX idx_comparaciones_usuario
    ON comparaciones (id_usuario);

CREATE INDEX idx_detalle_comparacion_oferta
    ON detalle_comparacion (id_detalle_cotizacion);

CREATE INDEX idx_ingresos_inventario_proveedor
    ON ingresos_inventario (id_proveedor);

CREATE INDEX idx_ingresos_inventario_fecha
    ON ingresos_inventario (fecha_ingreso);

CREATE INDEX idx_detalle_ingreso_producto
    ON detalle_ingreso_inventario (id_producto);

CREATE INDEX idx_detalle_ingreso_fecha
    ON detalle_ingreso_inventario (fecha_ingreso);

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
