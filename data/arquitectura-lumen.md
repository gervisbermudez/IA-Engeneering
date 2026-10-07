# Arquitectura de Lumen

Lumen es la plataforma interna de observabilidad del equipo de plataforma. Recibe métricas, logs y trazas de los servicios de producción y los deja consultables desde un solo lugar. No es un producto comercial: no tiene precios, planes de suscripción ni clientes externos.

## Componentes

El borde de entrada es el servicio `lumen-ingest`. Escucha en el puerto 8420 y acepta tres protocolos: OTLP gRPC, OTLP HTTP y el formato remoto de Prometheus. Cada muestra que entra se valida (nombre de métrica, etiquetas obligatorias y tamaño del payload) y se escribe en un buffer local en disco antes de confirmar el envío al productor.

El buffer de `lumen-ingest` tiene un tope de 2 GB por nodo. Si el disco del buffer supera ese tope, el nodo deja de aceptar muestras nuevas y responde HTTP 429 con el cuerpo `buffer_full`. El productor debe reintentar con backoff. No se descartan muestras que ya fueron aceptadas: permanecen en el buffer hasta que el writer las confirme en el almacén.

Detrás del borde hay un writer llamado `lumen-store`. Agrupa muestras por serie temporal y las compacta en bloques de 2 horas. Cada bloque se guarda en almacenamiento de objetos con la clave `tenant/servicio/fecha/bloque`. El índice de series vive en un nodo de metadatos aparte y no se mezcla con los bloques de muestras.

La API de consulta se llama `lumen-query`. No lee el buffer de ingesta. Solo lee bloques ya compactados y el índice de series. Por eso una muestra recién aceptada puede tardar hasta 2 minutos en aparecer en un gráfico. Ese retraso se llama *visibilidad de consulta* y está documentado como máximo de 120 segundos en condiciones normales.

## Etiquetas obligatorias

Toda serie temporal debe traer estas etiquetas: `service`, `env` y `region`. `env` solo admite `dev`, `staging` o `prod`. Si falta una etiqueta obligatoria, `lumen-ingest` rechaza la muestra con HTTP 400 y el código `missing_label`. No se rellenan etiquetas por defecto.

La etiqueta `tenant` es opcional. Si no viene, el writer usa el tenant `platform`. Los equipos de producto deben enviar su propio `tenant` para no mezclar series con las de plataforma.

## Capacidad de referencia

Un nodo de `lumen-ingest` está dimensionado para 80.000 muestras por segundo de forma sostenida. El clúster de producción corre 4 nodos de ingesta, así que el techo de diseño del borde es 320.000 muestras por segundo. Por encima de ese ritmo el buffer crece y, si se sostiene, termina en `buffer_full`.

`lumen-query` atiende consultas PromQL y un subconjunto de TraceQL limitado a búsqueda por `trace_id` y por `service`. No evalúa joins entre métricas y logs en la misma consulta. Esa composición la hace el panel de Lumen en el navegador, con dos pedidos separados.
