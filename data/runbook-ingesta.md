# Runbook de ingesta de Lumen

Procedimiento del turno de plataforma cuando la ingesta de Lumen se degrada. Aplica solo a `lumen-ingest` y al writer `lumen-store`. No cubre fallos de `lumen-query`.

## Síntoma: los productores reciben HTTP 429

1. Confirmar que el cuerpo de la respuesta es `buffer_full`. Si el cuerpo es otro, este runbook no aplica y hay que escalar al dueño del contrato de ingesta.
2. En cada nodo de ingesta, revisar el uso del buffer en disco. El tope configurado es 2 GB. Un nodo por encima de 1,6 GB se considera caliente aunque todavía no rechace tráfico.
3. Identificar el `service` que más muestras empujó en los últimos 10 minutos. Si un solo servicio explica más del 40 % del tráfico del nodo, contactar a ese equipo para que baje la cardinalidad o el ritmo de scrape antes de sumar nodos.
4. Si el tráfico está repartido y los cuatro nodos de producción están calientes, el clúster llegó al techo de diseño de 320.000 muestras por segundo. Escalar horizontalmente no está autorizado en este runbook: requiere cambio de capacidad aprobado. Mientras tanto, se mantiene el 429 para proteger el disco.

No se debe borrar el directorio del buffer para "liberar espacio". Ahí están muestras ya aceptadas que el writer todavía no compactó. Borrarlas es pérdida de datos.

## Síntoma: la compactación no avanza

La alerta `LumenStoreCompactionStuck` indica que un bloque de 2 horas lleva más de 30 minutos sin cerrarse.

1. Reiniciar solo el worker de compactación del shard que marca la alerta. El comando operativo es `lumen-store restart-compactor --shard <id>`.
2. Esperar 10 minutos. El bloque debe pasar a estado `sealed`.
3. Si sigue abierto, no reintentar el reinicio más de una vez. Escalar al equipo de almacenamiento con el id del bloque y el shard.

Está prohibido marcar un bloque como `sealed` a mano. Un bloque sellado a mano queda ilegible para `lumen-query` y hay que reconstruirlo desde la copia de las últimas 48 horas, si es que entra en esa ventana.

## Síntoma: muestras aceptadas que no se ven en los gráficos

Si el productor recibió HTTP 202 y el gráfico sigue vacío, medir la edad de la muestra. La visibilidad de consulta normal es de hasta 120 segundos. Antes de ese plazo no hay incidente.

Si pasaron más de 120 segundos y la muestra sigue sin aparecer, revisar si el writer está compactando (sección anterior). La API de consulta no lee el buffer: hasta que el bloque no se compacta, la muestra no existe para `lumen-query`.

## Después del incidente

Toda intervención de este runbook se anota en el canal de plataforma con: nodo o shard, hora UTC, comando ejecutado y si hubo pérdida de muestras. Si hubo pérdida, el SLO de ingesta del mes queda afectado y hay que registrarlo en el presupuesto de error. No hace falta abrir un documento aparte: el mensaje del canal es el registro.
