# Radar de Tendencias · ElMayorista

## Uso actual: un botón

Entra al radar y pulsa **Buscar tendencias**. Los resultados recibidos se
presentan en tarjetas. Las categorías **Hogar, Limpieza, Juegos y juguetes,
Películas, Navidad y Regalos**, y el selector Google/TikTok solo filtran lo
ya encontrado; no requieren registrar productos, escribir términos ni importar
CSV. Los detalles técnicos están en «Sobre las fuentes y la conexión».

No se promete un catálogo completo de «todos los productos en tendencia»:
ninguna de las fuentes conectadas ofrece esa cobertura. No se incorporan
ejemplos como squishy o tazas navideñas salvo que los devuelva una fuente.

## Fuentes y activación (una sola vez, por un administrador)

### Sin claves: Google RSS

El botón consulta el feed oficial de Google Trends para Perú. Se descartan las
consultas que no coinciden con el vocabulario comercial de
`services/radar_automatico.py`. La clasificación es una heurística de texto,
no un reconocimiento infalible de productos: puede omitir productos desconocidos
o conservar consultas informativas. No se interpreta una noticia como demanda
de merchandising ni se leen noticias para inventar nombres de productos.

**El feed es general y puede devolver cero coincidencias comerciales.** No sirve
para garantizar búsquedas específicas de productos, ni para medir todo el
mercado. Cuando no hay resultados, la página lo indica y no se rellena con datos
ficticios, productos del catálogo o ejemplos estacionales.

### Conexión comercial opcional: Google Trends y videos de TikTok

Se preparó un adaptador para **SerpApi**, un proveedor externo, no una API oficial
de Google ni TikTok. Requiere cuenta, clave, cuota y revisión de sus condiciones
y coste. No se contrató ni activó ningún servicio de pago.

Una vez aprobado por el responsable, añadir a `config/.env` y reiniciar:

```dotenv
SERPAPI_API_KEY=tu_clave_real
RADAR_SERPAPI_ENABLED=true
```

**Una clave sola no activa el proveedor.** Habilitarlo autoriza hasta **12
solicitudes por actualización**, seis a Google y seis a TikTok. Se ejecutan como
máximo tres simultáneamente, sin paginación ni reintentos. Cada petición tiene
timeout de 15 segundos y límite de respuesta de 2 MB. La última consulta de la
sesión se reutiliza durante 15 minutos, incluso si está vacía o parcialmente
fallida. Cambiar de categoría/fuente no consume cuota; abrir la página tampoco.

- **Google**: `engine=google_trends`, `data_type=RELATED_QUERIES`, `geo=PE`,
  `date=today 1-m`. Se exploran seis términos de referencia definidos en
  `config/radar.py`, automáticamente. Estas referencias son ámbitos de búsqueda,
  **no productos detectados**. Solo se muestran consultas devueltas y filtradas.
  - `rising`: crecimiento respecto al periodo anterior; no cuota de mercado.
  - `top`: índice relativo 0–100 dentro de las consultas relacionadas de su
    referencia, no cantidad de búsquedas ni ranking entre categorías.
  - Si una consulta está en ambos grupos se conserva el crecimiento, sin sumar
    ni mezclar las métricas. Se elimina duplicación entre referencias.
  - No se usa el índice relativo para ordenar un supuesto ranking global.
- **TikTok**: `engine=tiktok_discover`, con una referencia comercial por categoría.
  Devuelve videos y, cuando está disponible, reproducciones. **No devuelve cuántas
  veces se buscó un producto**, no confirma popularidad en Perú y no incorpora
  filtro temporal. La tarjeta señala esas limitaciones. Un video antiguo no se
  transforma en tendencia actual; se conserva su fecha de publicación cuando la
  fuente la proporciona. Videos repetidos se deduplican por URL.
- **Películas/Navidad genérica**: se etiquetan como temas, no como productos
  validados ni oportunidades probadas de merchandising.

Los contratos del adaptador comercial están cubiertos con fixtures de pruebas.
**No se verificó una consulta comercial en vivo con credenciales**, por lo que
su disponibilidad, cuota y cobertura deben comprobarse al activar la cuenta.
La conexión RSS sí se comprueba con respuestas reales, sin coste.

### Búsquedas más consultadas de TikTok: pendiente

No confundir reproducciones, hashtags o anuncios con búsquedas de productos.
Para consultar búsquedas populares, TikTok ofrece **Creator Search Insights**
con acceso y disponibilidad propios; la ayuda del radar enlaza a esa herramienta.
Esta versión no automatiza sus datos ni afirma tener su ranking.

TikTok Research API exige aprobación y uso de investigación elegible, no este
uso comercial de una tienda peruana. Commercial Content API declara cobertura
de anuncios de la UE, no búsquedas de productos en Perú. La API oficial de
Google Trends sigue documentada como alpha por solicitud. No se inventan
endpoints ni se evaden restricciones de acceso.

## Historial en PostgreSQL (opcional)

La consulta funciona aunque el historial no esté instalado. Para conservar los
resultados entre sesiones, ejecutar `database/radar_busqueda_automatica.sql`
sobre la base configurada. Solo crea `radar_busquedas`, con el resultado JSONB,
usuario creador y fecha de guardado. Requiere la tabla existente `usuarios`.
No cambia ventas, catálogo ni abastecimiento. No incluye datos de ejemplo.

Al abrir la página se recupera la última búsqueda compartida, indicando su
fecha real. Eso no dispara peticiones ni presenta la carga del historial como
una búsqueda nueva. Si falla la red se conserva lo mostrado; si falla el
guardado, el resultado sigue visible y el aviso está en la ayuda de fuentes.
Una respuesta parcial se identifica y conserva sus avisos por categoría/fuente.

La migración anterior `radar_tendencias.sql` y sus servicios manuales se
conservan por compatibilidad con datos y pruebas de la primera implementación,
pero **ya no son necesarios para usar la nueva pantalla**. No se borran tablas
ni seguimientos existentes. El flujo CSV/manual anterior no está expuesto en
la interfaz principal.

## Arquitectura

El repositorio es una aplicación de escritorio **Python/PySide6**, no una web.
Se reutiliza su arquitectura sin nuevas dependencias:

- `views/tendencias_view.py`: botón, categorías, tarjetas y ayuda secundaria;
  reutiliza `_BaseIntelligenceView` y el shell existente.
- `controllers/tendencias_controller.py`: coordinación mediante `QThread` y
  señales, sin bloquear la interfaz.
- `services/tendencias_service.py`: acciones `buscar_radar` y `cargar_radar`;
  almacenamiento opcional e independiente de la obtención de señales.
- `services/radar_automatico.py`: obtención, filtrado, deduplicación y caché de
  resultados. Separa métricas de Google y TikTok.
- `services/fuentes_tendencias.py`: cliente RSS previamente implementado.
- `repositories/tendencias_repository.py`: SQL parametrizado mediante la
  conexión existente `config.database.obtener_conexion`.
- `config/radar.py`: ámbitos de búsqueda y activación explícita del proveedor.

No se generan fotografías: las tarjetas usan iconos de categoría identificados
como tales. No se crean productos, previsiones, compras o cantidades de
abastecimiento a partir de estas señales. Las claves no se guardan en snapshots,
enlaces visibles ni mensajes de error.

## Pruebas

```powershell
python -B -m unittest discover -s tests -v
```

Para incluir PostgreSQL configurado, con permiso para crear esquemas:

```powershell
$env:FLAMAR_TEST_DB = '1'
python -B -m unittest discover -s tests -v
```

Las pruebas de base de datos crean un esquema aleatorio y hacen rollback al
terminar: no almacenan datos sintéticos en `public`. Los datos de prueba solo
existen en tests. Se cubren el botón único, filtros sin peticiones adicionales,
fuentes no configuradas, caché, respuestas vacías, fallos parciales, contratos
del proveedor, métricas diferenciadas y persistencia del historial.

## Documentación de las fuentes

- [Google Trending Now y RSS](https://support.google.com/trends/answer/3076011?hl=es)
- [Normalización de Google Trends](https://support.google.com/trends/answer/4365533?hl=es)
- [Google Trends API alpha](https://developers.google.com/search/apis/trends)
- [SerpApi: Google Trends Related Queries](https://serpapi.com/google-trends-related-queries)
- [SerpApi: TikTok Discover](https://serpapi.com/tiktok-discover-api)
- [TikTok: Creator Search Insights](https://support.tiktok.com/en/using-tiktok/growing-your-audience/creator-search-insights)
- [TikTok Research API](https://developers.tiktok.com/products/research-api)
- [TikTok Commercial Content API](https://developers.tiktok.com/products/commercial-content-api)

Confirmar condiciones y cobertura al activar cualquier proveedor.
