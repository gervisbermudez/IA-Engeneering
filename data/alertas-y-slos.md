# Alertas y SLOs de Lumen

Este documento fija los objetivos de nivel de servicio de la plataforma Lumen y las alertas que el equipo de plataforma pagina. No describe SLOs de los servicios que Lumen observa: cada equipo dueño define los suyos.

## SLO de la API de consulta

El SLO de `lumen-query` es 99,9 % de disponibilidad mensual. La ventana es el mes calendario, en hora UTC. Una consulta cuenta como fallida si responde HTTP 5xx o si tarda más de 8 segundos en devolver el primer byte. Los HTTP 400 por PromQL inválido no cuentan contra el SLO: son error del cliente.

El presupuesto de error de ese 99,9 % es aproximadamente 43 minutos de indisponibilidad al mes. Cuando se consumió el 50 % del presupuesto en lo que va del mes, queda prohibido desplegar cambios de `lumen-query` que no sean un arreglo de un incidente abierto. El control lo hace el pipeline de despliegue leyendo el burn rate publicado por la propia plataforma.

## SLO de ingesta

El SLO de `lumen-ingest` es 99,95 % de aceptación mensual. Una muestra cuenta como no aceptada si el borde responde 429 o 5xx. Los HTTP 400 por etiqueta faltante o payload inválido no entran en el cálculo: el cliente envió algo que el contrato rechaza.

No hay SLO de frescura distinto de la visibilidad de consulta. El máximo admitido para que una muestra aceptada aparezca en `lumen-query` sigue siendo 120 segundos, definido en la arquitectura. Si la mediana de ese retraso supera 90 segundos durante 15 minutos, se dispara la alerta `LumenQueryLagHigh`, pero eso no abre por sí solo una violación de SLO.

## Alertas que paginan

Estas alertas despiertan al turno de plataforma:

- `LumenIngestBufferFull`: algún nodo de ingesta respondió `buffer_full` más de 30 veces en 5 minutos. Acción inicial: revisar si un productor se disparó y, si hace falta, escalar el nodo que está lleno.
- `LumenQueryAvailabilityBurn`: el burn rate de 1 hora del SLO de consulta supera 14. Acción inicial: mirar errores 5xx de `lumen-query` y el estado del índice de series.
- `LumenStoreCompactionStuck`: un bloque de 2 horas lleva más de 30 minutos sin compactarse. Acción inicial: reiniciar el worker de compactación del shard afectado. No borrar el bloque a mano.

La alerta `LumenQueryLagHigh` solo notifica en el canal de plataforma. No pagina de noche.

## Silencios

Un silencio de alerta no puede durar más de 4 horas. Para extenderlo hay que crear otro silencio con un motivo nuevo. No existe un silencio permanente. El sistema rechaza silencios cuya duración supere 14400 segundos.
