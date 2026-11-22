# Radar de tendencias: fuentes reales y operación

## Qué cambió

El radar anterior consultaba el RSS general de Google Perú y solo conservaba términos de un vocabulario comercial. Ese RSS es principalmente actualidad y **no descubre un catálogo de productos**. El proveedor opcional SerpApi no resolvía el requisito de gratuidad ni confirmaba Perú en TikTok.

El flujo activo ahora usa exclusivamente RSS oficial, CSV aportados por el usuario y, si se dispone de acceso autorizado, TikTok Discovery API. **No usa SerpApi, pytrends, endpoints privados, navegadores automatizados, cookies ni scraping.** Las antiguas variables de SerpApi no activan consumo.

Los resultados son señales/candidatos, no productos validados, ventas ni recomendaciones automáticas de compra. Los hashtags y consultas sin clasificar se conservan en «Por clasificar». No se generan resultados desde el vocabulario, no se insertan ejemplos y no se altera el catálogo.

## Investigación (12 de noviembre de 2026)

### TikTok Discovery API

La [introducción oficial](https://business-api.tiktok.com/portal/docs/discovery-api-overview/v1.3) describe el proceso: cuenta TikTok For Business → registro de desarrollador → app → autorización de la cuenta pertinente → token → solicitudes. No es una API pública anónima. La app debe tener acceso aprobado a los productos/permisos correspondientes; crear una app o poner un token en `.env` no garantiza acceso. Hay cuotas y restricciones del proveedor. No se verificó aquí ningún coste contractual: no se incorpora un servicio de pago, pero tampoco se garantiza que TikTok conceda acceso gratuito a cualquier cuenta.

| Función | Endpoint GET v1.3 | Requisitos y límites |
|---|---|---|
| Hashtags populares | `discovery/trending_list/` | Token de anunciante, `advertiser_id`, `discovery_type=HASHTAG`; filtros `country_code`, `date_range`, categoría. Hasta 200 hashtags. Son hashtags, no SKU. |
| Búsquedas en tendencia | `discovery/trending/search/` | Token de cuenta TikTok Business con `discovery.search.words`; `business_id` es el `open_id` de esa cuenta en la app. `is_personalized=false`. Devuelve hasta 20 palabras/frases, **sin país ni volumen** en este contrato. |

Para hashtags se autoriza una cuenta publicitaria mediante el flujo Marketing API y se obtiene su token/advertiser ID. Para búsquedas se usa el flujo de autorización de la cuenta TikTok Business, `tt_user/oauth2/token/` y se puede revisar el scope con `tt_user/token_info/get/`. No son tokens intercambiables. El propietario debe consentir «Query for recommended search terms based on trends or specific keywords» para `discovery.search.words`. Un token de Login Kit común no sustituye estos permisos.

Referencias técnicas: [hashtags en el portal oficial](https://business-api.tiktok.com/portal/docs?id=1825119032526849), [búsquedas en el portal oficial](https://business-api.tiktok.com/portal/docs?id=1832798345014338). El portal sirve una aplicación JavaScript y no devolvió el cuerpo de estos documentos al cliente de texto utilizado durante la investigación. Se contrastaron los contratos con [una reproducción del documento de hashtags](https://www.xmcsl.cn/project/knowledge-assets/documents/8ed1e4e600ca0eeec453.md) y [una reproducción de búsquedas](https://www.xmcsl.cn/project/knowledge-assets/documents/5568e24bbcd0591809fe.md), además de [los requisitos publicados por Sprinklr](https://www.sprinklr.com/help/articles/tiktok/tiktok-discovery/67d2d7fa3daa3c66bcecb77c/). Las reproducciones no son documentación oficial ni garantía de vigencia: revisar permisos y contratos en el portal con la cuenta antes de activar producción.

**Perú:** no se pudo certificar la lista de mercados habilitados para tu cuenta. El conector solicita exclusivamente `PE`, `ALL`, `7DAY` y exige que `filter_info` confirme país y ventana. Si TikTok rechaza Perú, cambia filtros o no confirma la cobertura, muestra un aviso; **no cambia silenciosamente a US/MX ni etiqueta datos globales como peruanos**. Las búsquedas se guardan con país no informado.

La Research API de TikTok no se utiliza como atajo comercial: tiene elegibilidad y usos permitidos diferentes.

### TikTok Creative Center

La [ayuda oficial, actualizada en julio de 2026](https://ads.tiktok.com/help/article/top-products?lang=en), lo presenta como centro público gratuito; recomienda iniciar sesión para más datos. El enlace antiguo de Top Products actualmente muestra la página general, no un contrato de exportación. La [guía actual de Trends](https://ads.tiktok.com/help/article/trend-discovery?lang=en) documenta hashtags, filtros y «See Analytics» (curva, videos relacionados, audiencias, popularidad regional).

No se confirmó una exportación CSV general ni RSS público de Creative Center. Algunas funciones cambian por región/cuenta. **No se promete un botón de descarga que no esté disponible.** Si tu interfaz ofrece una exportación permitida, adapta esos datos a la plantilla; si no, registra manualmente lo visible, conservando enlace, fecha, país realmente mostrado, filtros y unidad. Los productos/categorías de anuncios y su popularidad no equivalen a ventas de TikTok Shop ni búsquedas de consumidores.

### Google Trends

- [Tendencias actuales](https://support.google.com/trends/answer/3076011?hl=en): exportación oficial gratuita CSV, portapapeles y RSS. El feed [`https://trends.google.com/trending/rss?geo=PE`](https://trends.google.com/trending/rss?geo=PE) respondió durante esta investigación. Es un subconjunto actual, no una lista exhaustiva, y puede contener **cero productos comerciales**. Los intervalos como `2000+` se guardan como texto, no como cifras exactas.
- [Exportar gráficos](https://support.google.com/trends/answer/4365538?hl=es): CSV de Explorar, incluidos histórico y consultas relacionadas. El radar admite estos CSV sin APIs privadas. En relacionadas y Tendencias actuales el usuario debe declarar país/contexto porque no todos los archivos los incluyen de forma verificable.
- [Interpretación oficial](https://support.google.com/trends/answer/4365533?hl=es): interés normalizado 0–100, no búsquedas absolutas; una subida no prueba demanda comercial.
- La [API oficial de Google Trends](https://developers.google.com/search/apis/trends) sigue anunciando acceso alpha mediante solicitud y selección. No se asume acceso universal; no se sustituye por scraping si falta autorización.

## Instalación

Requisitos Python del proyecto sin dependencias adicionales: PySide6 incluye QtCharts, psycopg y python-dotenv ya están declarados.

Sobre la base PostgreSQL existente, ejecutar **solo**:

```powershell
psql -h localhost -U postgres -d flamar -f database/radar_datos_reales.sql
```

Adaptar host/usuario/base a `config/.env`. La migración es aditiva e idempotente, crea `radar_lotes` y `radar_senales`; no necesita las dos migraciones de radar anteriores, no las borra ni transforma sus snapshots. No hay importación automática de históricos antiguos sin contexto verificable. El usuario PostgreSQL necesita permisos para crear tablas y el usuario de la aplicación permisos de lectura/escritura.

Sin migración/conexión se pueden consultar fuentes en memoria, con advertencia visible de **no guardado**. Las importaciones y el histórico no se presentan como exitosos si falla PostgreSQL.

## Uso gratuito sin autorización TikTok

1. Abrir Radar → **Abrir TikTok Creative Center**. Revisar manualmente las tendencias y evidencia accesible para tu cuenta; no eludir login/restricciones. No asumir Perú por el idioma del video.
2. Radar → **Importar CSV real** → TikTok → **Guardar plantilla TikTok vacía**. Solo contiene encabezados, ningún producto o métrica de ejemplo.
3. Completar con observaciones reales autorizadas; guardar UTF-8, separado por comas:

| Columna | Contenido |
|---|---|
| `termino` | Nombre del producto observado o texto exacto de consulta/hashtag (1–200 caracteres). |
| `tipo` | `producto`, `hashtag`, `consulta`, `tema` o `video`. Producto es una clasificación manual, no validación automática. |
| `categoria` | `hogar`, `limpieza`, `juegos`, `peliculas`, `navidad`, `regalos`, `otros`. |
| `pais` | `PE`, `US`, `MX`, `CL`, `CO`, `BR`; **`ND` si no está informado**. |
| `fecha` | Fecha de observación `AAAA-MM-DD`, no futura. |
| `metrica` | `reproducciones`, `publicaciones`, `popularidad`, `posicion`, `crecimiento`, `presencia`. |
| `valor` | Solo cifra exacta, sin separadores, punto decimal. Vacío si es abreviada, censurada o ausente. Presencia no lleva cifra. |
| `valor_original` | Texto visible, incluidas abreviaturas o valores censurados. No se transforma `1.2M` en un número pretendidamente exacto. |
| `periodo` | Ventana exacta mostrada: no mezclar 7 días, 30 días y acumulados. |
| `contexto` | Mismos filtros, categoría, ámbito y escala para comparar fechas. Para videos/productos diferentes del mismo nombre, incluir el identificador/enlace en el contexto. **Si la escala se renormaliza, cambiar contexto** para no unir series incompatibles. |
| `url` | Evidencia HTTPS de `tiktok.com`/`ads.tiktok.com` o subdominio legítimo. |

4. Validar/previsualizar. Revisar país, tipo, fecha y valores. Cancelar no escribe nada. Confirmar guarda lote y observaciones en una transacción. El servicio vuelve a leer el archivo y exige la misma huella confirmada.
5. Para descubrir más candidatos: Google Trends → Explorar Perú → consulta de categoría que elijas → **Consultas relacionadas → Descargar CSV**. Importar como relacionadas, declarando origen, periodo y fecha. Se importan los términos reales TOP/RISING, incluidos desconocidos, sin rellenar con semillas. «Breakout» permanece sin porcentaje numérico. También se admite el CSV de Tendencias actuales con cabeceras inglesas/españolas soportadas; el volumen abreviado queda como texto.
6. Para analizar un candidato: Google Trends → un solo término exacto, un país, datos diarios/semanales/mensuales → descargar **Interés a lo largo del tiempo** → importar como histórico. El encabezado debe coincidir con el país. Los CSV de varias comparaciones o resolución horaria no se admiten. Marcar último punto parcial si aún no está completo.
7. **Ver histórico y crecimiento** abre un gráfico y tabla de los puntos reales guardados. Para observaciones manuales, importar nuevas fechas con los mismos filtros/ventana. Un único punto no genera una curva ni crecimiento inventado.

## Activar Discovery únicamente con acceso concedido

Opcionalmente agregar a `config/.env` (archivo ignorado por Git):

```dotenv
RADAR_TIKTOK_ENABLED=true
TIKTOK_ADVERTISER_ID=
TIKTOK_ADVERTISER_ACCESS_TOKEN=
TIKTOK_BUSINESS_ID=
TIKTOK_BUSINESS_ACCESS_TOKEN=
```

Completar solo el par autorizado que corresponda, o ambos. No publicar tokens, app secrets ni capturarlos en registros. Reiniciar la app después de cambios. No se implementa una falsa pantalla «Conectar»: el administrador obtiene/renueva los tokens mediante el flujo oficial de TikTok (app aprobada, redirect URI registrado, consentimiento y canje seguro de código). El radar no conserva app secrets ni realiza refresh automático. Ante expiración/401/403/429 o permisos insuficientes, muestra error y mantiene datos previos. API configurada **no** significa autorizada ni conectada con éxito. No fue posible una prueba en vivo de Discovery sin credenciales autorizadas.

Buscar hace como máximo una solicitud de hashtags, una de búsquedas y una RSS (solo las configuradas), sin paginación, reintentos ni fallback de mercado. Reutiliza resultados durante 15 minutos en la sesión. Al abrir la pantalla solo se consulta PostgreSQL; no hay sondeo ni programación oculta. La actualización es por botón o importación.

## Historial, gráficos y límites

- Arquitectura: vista PySide6 → `TendenciasController`/worker → `TendenciasService` → fuentes/importador → `TendenciasRepository` → PostgreSQL.
- Cada lote guarda origen, archivo, SHA256, usuario y fecha de ingreso; los puntos conservan texto original, país, tipo, métrica, contexto, fecha observada, parcial y URL. SHA256 verifica integridad/deduplicación, **no autenticidad de un CSV manual**.
- Mismo archivo/contexto no se duplica. Las consultas idénticas del mismo día no añaden artificialmente puntos. Para correcciones de la misma fecha/serie, se conserva auditoría de todos los lotes y el gráfico muestra la última revisión. Se retiene el historial sin borrado automático.
- Cada serie separa término normalizado, tipo, fuente, origen, país, unidad y contexto. Cada exportación de Google usa su SHA256 como escala propia: **no se concatenan archivos de escalas 0–100 diferentes**, ni se comparan países como volúmenes equivalentes.
- El gráfico solo traza cifras exactas completas. Los puntos parciales, `<1`, ausentes y «Breakout» se muestran en tabla y no se rellenan. Eje temporal UTC. Posición se muestra invertida (menor es mejor).
- El cambio es `(último − anterior) / anterior × 100`, entre los últimos dos puntos completos de la **misma** serie, con fechas explícitas. Base cero, cifras ausentes o insuficientes: no calculable. Posición: diferencia de puestos. No se calcula «crecimiento del crecimiento» ni porcentajes sobre presencia/tráfico textual.
- El radar no verifica stock, proveedor, SKU, autenticidad, ventas, estacionalidad ni viabilidad comercial. Lo observado fuera de Perú requiere validación local. La antigüedad se muestra por señal, sin disimular datos viejos como actuales.

## Verificación

```powershell
python -m unittest discover -s tests -v
```

Integración optativa PostgreSQL (esquema aleatorio y rollback, sin tocar datos comerciales):

```powershell
$env:FLAMAR_TEST_DB = '1'
python -m unittest discover -s tests -p test_tendencias_db.py -v
```

Los fixtures sintéticos existen exclusivamente en tests y nunca se cargan en el radar real. Las pruebas cubren contratos API, bloqueo sin autorización, país no confirmado, importaciones, censurados, vista previa, huellas, deduplicación, escalas, gráficos y almacenamiento.
