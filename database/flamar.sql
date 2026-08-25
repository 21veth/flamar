-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 25-08-2026 a las 22:17:06
-- Versión del servidor: 10.6.20-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `flamar`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categoria`
--

CREATE TABLE `categoria` (
  `id_categoria` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `compras`
--

CREATE TABLE `compras` (
  `id_compra` int(11) NOT NULL,
  `id_consumidor` int(11) NOT NULL,
  `id_tienda` int(11) NOT NULL,
  `id_promocion` int(11) DEFAULT NULL,
  `fecha_compra` date NOT NULL,
  `hora_compra` time DEFAULT NULL,
  `total` decimal(10,2) NOT NULL,
  `metodo_pago` varchar(50) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `consumidores`
--

CREATE TABLE `consumidores` (
  `id_consumidor` int(11) NOT NULL,
  `codigo_consumidor` varchar(20) DEFAULT NULL,
  `genero` varchar(20) DEFAULT NULL,
  `distrito` varchar(100) DEFAULT NULL,
  `rango_edad` enum('18-25','26-35','36-45','mas de 45') DEFAULT NULL,
  `fecha_registro` date DEFAULT curdate(),
  `estado` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `detalle_compra`
--

CREATE TABLE `detalle_compra` (
  `id_detalle` int(11) NOT NULL,
  `id_compra` int(11) NOT NULL,
  `id_producto` int(11) NOT NULL,
  `cantidad` int(11) DEFAULT NULL,
  `precio_unitario` decimal(10,2) DEFAULT NULL,
  `descuento` decimal(10,2) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `errores_preprocesamiento`
--

CREATE TABLE `errores_preprocesamiento` (
  `id_error` int(11) NOT NULL,
  `id_importacion` int(11) NOT NULL,
  `numero_fila` int(11) DEFAULT NULL,
  `campo` varchar(255) DEFAULT NULL,
  `valor_original` text DEFAULT NULL,
  `problema` text DEFAULT NULL,
  `valor_corregido` text DEFAULT NULL,
  `corregido` tinyint(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `importaciones`
--

CREATE TABLE `importaciones` (
  `id_importacion` int(11) NOT NULL,
  `id_usuario` int(11) NOT NULL,
  `nombre_archivo` varchar(255) DEFAULT NULL,
  `tipo_archivo` varchar(255) DEFAULT NULL,
  `registros_totales` int(11) DEFAULT NULL,
  `registros_validos` int(11) DEFAULT NULL,
  `registros_error` int(11) DEFAULT NULL,
  `fecha_importacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `estado` varchar(30) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `metricas_consumidor`
--

CREATE TABLE `metricas_consumidor` (
  `id_metrica` int(11) NOT NULL,
  `id_consumidor` int(11) NOT NULL,
  `total_compras` int(11) NOT NULL,
  `frecuencia_compra` decimal(10,2) DEFAULT NULL,
  `gasto_total` decimal(10,2) DEFAULT NULL,
  `gasto_promedio` decimal(10,2) DEFAULT NULL,
  `ultima_compra` date DEFAULT NULL,
  `sensibilidad_descuento` decimal(10,2) DEFAULT NULL,
  `nivel_lealtad` varchar(20) DEFAULT NULL,
  `fecha_calculo` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `modelos_mineria`
--

CREATE TABLE `modelos_mineria` (
  `id_modelo` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `algoritmo` varchar(100) DEFAULT NULL,
  `version` varchar(100) DEFAULT NULL,
  `parametros` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`parametros`)),
  `precision_modelo` decimal(5,2) DEFAULT NULL,
  `fecha_entrenamiento` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `estado` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `predicciones`
--

CREATE TABLE `predicciones` (
  `id_prediccion` int(11) NOT NULL,
  `id_consumidor` int(11) NOT NULL,
  `id_modelo` int(11) NOT NULL,
  `tipo_prediccion` varchar(150) DEFAULT NULL,
  `resultado` varchar(150) DEFAULT NULL,
  `probabilidad` decimal(5,2) DEFAULT NULL,
  `nivel_confianza` varchar(100) DEFAULT NULL,
  `periodo_predicho` date DEFAULT NULL,
  `fecha_generacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `id_producto` int(11) NOT NULL,
  `id_categoria` int(11) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `precio_referencia` decimal(10,2) DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `promociones`
--

CREATE TABLE `promociones` (
  `id_promocion` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `porcentaje_descuento` decimal(5,2) DEFAULT NULL,
  `fecha_inicio` date DEFAULT NULL,
  `fecha_fin` date DEFAULT NULL,
  `descripcion` text DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `reglas_asociacion`
--

CREATE TABLE `reglas_asociacion` (
  `id_regla` int(11) NOT NULL,
  `id_producto_antecedente` int(11) NOT NULL,
  `id_producto_consecuente` int(11) NOT NULL,
  `id_modelo` int(11) NOT NULL,
  `soporte` decimal(10,6) DEFAULT NULL,
  `confianza` decimal(10,6) DEFAULT NULL,
  `lift` decimal(10,6) DEFAULT NULL,
  `fecha_analisis` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `segmentacion_consumidor`
--

CREATE TABLE `segmentacion_consumidor` (
  `id_segmentacion` int(11) NOT NULL,
  `id_consumidor` int(11) NOT NULL,
  `id_segmento` int(11) NOT NULL,
  `id_modelo` int(11) NOT NULL,
  `distancia_centroide` decimal(10,4) DEFAULT NULL,
  `fecha_analisis` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `segmentos`
--

CREATE TABLE `segmentos` (
  `id_segmento` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tiendas`
--

CREATE TABLE `tiendas` (
  `id_tienda` int(11) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `categoria_tienda` varchar(100) DEFAULT NULL,
  `ubicacion` varchar(100) DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id_usuario` int(11) NOT NULL,
  `usuario` varchar(100) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `rol` enum('gerente','trabajador','administrador') DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  `ultimo_acceso` timestamp NULL DEFAULT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `categoria`
--
ALTER TABLE `categoria`
  ADD PRIMARY KEY (`id_categoria`);

--
-- Indices de la tabla `compras`
--
ALTER TABLE `compras`
  ADD PRIMARY KEY (`id_compra`),
  ADD KEY `fk_compra_consumidor` (`id_consumidor`),
  ADD KEY `fk_compra_tienda` (`id_tienda`),
  ADD KEY `fk_compra_promocion` (`id_promocion`);

--
-- Indices de la tabla `consumidores`
--
ALTER TABLE `consumidores`
  ADD PRIMARY KEY (`id_consumidor`),
  ADD UNIQUE KEY `codigo_consumidor` (`codigo_consumidor`);

--
-- Indices de la tabla `detalle_compra`
--
ALTER TABLE `detalle_compra`
  ADD PRIMARY KEY (`id_detalle`),
  ADD KEY `fk_detalle_compra_compra` (`id_compra`),
  ADD KEY `fk_detalle_compra_producto` (`id_producto`);

--
-- Indices de la tabla `errores_preprocesamiento`
--
ALTER TABLE `errores_preprocesamiento`
  ADD PRIMARY KEY (`id_error`),
  ADD KEY `fk_errores_preprocesamiento_importacion` (`id_importacion`);

--
-- Indices de la tabla `importaciones`
--
ALTER TABLE `importaciones`
  ADD PRIMARY KEY (`id_importacion`),
  ADD KEY `fk_importaciones_usuario` (`id_usuario`);

--
-- Indices de la tabla `metricas_consumidor`
--
ALTER TABLE `metricas_consumidor`
  ADD PRIMARY KEY (`id_metrica`),
  ADD KEY `fk_metricas_consumidor_consumidor` (`id_consumidor`);

--
-- Indices de la tabla `modelos_mineria`
--
ALTER TABLE `modelos_mineria`
  ADD PRIMARY KEY (`id_modelo`);

--
-- Indices de la tabla `predicciones`
--
ALTER TABLE `predicciones`
  ADD PRIMARY KEY (`id_prediccion`),
  ADD KEY `fk_predicciones_consumidor` (`id_consumidor`),
  ADD KEY `fk_predicciones_modelo` (`id_modelo`);

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id_producto`),
  ADD KEY `fk_producto_categoria` (`id_categoria`);

--
-- Indices de la tabla `promociones`
--
ALTER TABLE `promociones`
  ADD PRIMARY KEY (`id_promocion`);

--
-- Indices de la tabla `reglas_asociacion`
--
ALTER TABLE `reglas_asociacion`
  ADD PRIMARY KEY (`id_regla`),
  ADD KEY `fk_reglas_asociacion_producto_antecedente` (`id_producto_antecedente`),
  ADD KEY `fk_reglas_asociacion_producto_consecuente` (`id_producto_consecuente`),
  ADD KEY `fk_reglas_asociacion_modelo` (`id_modelo`);

--
-- Indices de la tabla `segmentacion_consumidor`
--
ALTER TABLE `segmentacion_consumidor`
  ADD PRIMARY KEY (`id_segmentacion`),
  ADD KEY `fk_segmentacion_consumidor_consumidor` (`id_consumidor`),
  ADD KEY `fk_segmentacion_consumidor_segmento` (`id_segmento`),
  ADD KEY `fk_segmentacion_consumidor_modelo` (`id_modelo`);

--
-- Indices de la tabla `segmentos`
--
ALTER TABLE `segmentos`
  ADD PRIMARY KEY (`id_segmento`);

--
-- Indices de la tabla `tiendas`
--
ALTER TABLE `tiendas`
  ADD PRIMARY KEY (`id_tienda`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id_usuario`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `categoria`
--
ALTER TABLE `categoria`
  MODIFY `id_categoria` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `compras`
--
ALTER TABLE `compras`
  MODIFY `id_compra` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `consumidores`
--
ALTER TABLE `consumidores`
  MODIFY `id_consumidor` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `detalle_compra`
--
ALTER TABLE `detalle_compra`
  MODIFY `id_detalle` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `errores_preprocesamiento`
--
ALTER TABLE `errores_preprocesamiento`
  MODIFY `id_error` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `importaciones`
--
ALTER TABLE `importaciones`
  MODIFY `id_importacion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `metricas_consumidor`
--
ALTER TABLE `metricas_consumidor`
  MODIFY `id_metrica` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `modelos_mineria`
--
ALTER TABLE `modelos_mineria`
  MODIFY `id_modelo` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `predicciones`
--
ALTER TABLE `predicciones`
  MODIFY `id_prediccion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `id_producto` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `promociones`
--
ALTER TABLE `promociones`
  MODIFY `id_promocion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `reglas_asociacion`
--
ALTER TABLE `reglas_asociacion`
  MODIFY `id_regla` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `segmentacion_consumidor`
--
ALTER TABLE `segmentacion_consumidor`
  MODIFY `id_segmentacion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `segmentos`
--
ALTER TABLE `segmentos`
  MODIFY `id_segmento` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `tiendas`
--
ALTER TABLE `tiendas`
  MODIFY `id_tienda` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id_usuario` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `compras`
--
ALTER TABLE `compras`
  ADD CONSTRAINT `fk_compra_consumidor` FOREIGN KEY (`id_consumidor`) REFERENCES `consumidores` (`id_consumidor`),
  ADD CONSTRAINT `fk_compra_promocion` FOREIGN KEY (`id_promocion`) REFERENCES `promociones` (`id_promocion`),
  ADD CONSTRAINT `fk_compra_tienda` FOREIGN KEY (`id_tienda`) REFERENCES `tiendas` (`id_tienda`);

--
-- Filtros para la tabla `detalle_compra`
--
ALTER TABLE `detalle_compra`
  ADD CONSTRAINT `fk_detalle_compra_compra` FOREIGN KEY (`id_compra`) REFERENCES `compras` (`id_compra`),
  ADD CONSTRAINT `fk_detalle_compra_producto` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`);

--
-- Filtros para la tabla `errores_preprocesamiento`
--
ALTER TABLE `errores_preprocesamiento`
  ADD CONSTRAINT `fk_errores_preprocesamiento_importacion` FOREIGN KEY (`id_importacion`) REFERENCES `importaciones` (`id_importacion`);

--
-- Filtros para la tabla `importaciones`
--
ALTER TABLE `importaciones`
  ADD CONSTRAINT `fk_importaciones_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`);

--
-- Filtros para la tabla `metricas_consumidor`
--
ALTER TABLE `metricas_consumidor`
  ADD CONSTRAINT `fk_metricas_consumidor_consumidor` FOREIGN KEY (`id_consumidor`) REFERENCES `consumidores` (`id_consumidor`);

--
-- Filtros para la tabla `predicciones`
--
ALTER TABLE `predicciones`
  ADD CONSTRAINT `fk_predicciones_consumidor` FOREIGN KEY (`id_consumidor`) REFERENCES `consumidores` (`id_consumidor`),
  ADD CONSTRAINT `fk_predicciones_modelo` FOREIGN KEY (`id_modelo`) REFERENCES `modelos_mineria` (`id_modelo`);

--
-- Filtros para la tabla `productos`
--
ALTER TABLE `productos`
  ADD CONSTRAINT `fk_producto_categoria` FOREIGN KEY (`id_categoria`) REFERENCES `categoria` (`id_categoria`);

--
-- Filtros para la tabla `reglas_asociacion`
--
ALTER TABLE `reglas_asociacion`
  ADD CONSTRAINT `fk_reglas_asociacion_modelo` FOREIGN KEY (`id_modelo`) REFERENCES `modelos_mineria` (`id_modelo`),
  ADD CONSTRAINT `fk_reglas_asociacion_producto_antecedente` FOREIGN KEY (`id_producto_antecedente`) REFERENCES `productos` (`id_producto`),
  ADD CONSTRAINT `fk_reglas_asociacion_producto_consecuente` FOREIGN KEY (`id_producto_consecuente`) REFERENCES `productos` (`id_producto`);

--
-- Filtros para la tabla `segmentacion_consumidor`
--
ALTER TABLE `segmentacion_consumidor`
  ADD CONSTRAINT `fk_segmentacion_consumidor_consumidor` FOREIGN KEY (`id_consumidor`) REFERENCES `consumidores` (`id_consumidor`),
  ADD CONSTRAINT `fk_segmentacion_consumidor_modelo` FOREIGN KEY (`id_modelo`) REFERENCES `modelos_mineria` (`id_modelo`),
  ADD CONSTRAINT `fk_segmentacion_consumidor_segmento` FOREIGN KEY (`id_segmento`) REFERENCES `segmentos` (`id_segmento`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
