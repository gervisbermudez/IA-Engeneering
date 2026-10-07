# Retención de datos en Lumen

Lumen guarda tres señales: métricas, logs y trazas. Cada una tiene su propio plazo. Borrar antes de tiempo requiere un ticket aprobado por el equipo de plataforma y por el equipo dueño del servicio. No hay borrado self-service.

## Métricas

Las métricas de alta resolución (el scrape o el push tal como llegó, sin agregar) se retienen 15 días. A partir del día 16 solo quedan rollups.

Los rollups se calculan con dos ventanas:

- rollup de 5 minutos, retenido 90 días;
- rollup de 1 hora, retenido 13 meses.

Una consulta cuyo rango supera 15 días y pide un paso menor a 5 minutos recibe los rollups de 5 minutos, no las muestras crudas. `lumen-query` no reconstruye la alta resolución a partir de un rollup. Si el panel pide resolución cruda fuera de la ventana de 15 días, la API responde HTTP 422 con el código `resolution_expired`.

Los rollups no guardan el máximo ni el mínimo de la ventana. Guardan suma, conteo y el último valor. Un percentil calculado sobre un rango ya rollupeado es una aproximación y la interfaz lo marca con la leyenda "agregado".

## Logs

Los logs se retienen 7 días en caliente, consultables por texto y por `trace_id`. Después de 7 días pasan a almacenamiento frío por otros 30 días. El frío solo permite descarga por `service` y por día; no permite búsqueda de texto. A los 37 días desde la ingesta del log, el objeto frío se elimina.

Un log mayor a 256 KB se trunca en la ingesta. Se conservan los primeros 256 KB y se agrega el atributo `lumen.truncated=true`. El resto no se puede recuperar.

## Trazas

Las trazas se retienen 72 horas. No hay almacenamiento frío para trazas. Una traza cuyo span raíz es más viejo que 72 horas deja de aparecer en búsquedas por `service`. Si alguien guarda el `trace_id`, `lumen-query` igual responde que no existe una vez vencido el plazo.

Los spans con el atributo `lumen.keep=true` no extienden la retención. Ese atributo está reservado y hoy no cambia ningún plazo. Quien necesite conservar una traza debe exportarla fuera de Lumen antes de que venzan las 72 horas.

## Copias y restauración

Hay una copia diaria del índice de series y de los bloques de métricas de las últimas 48 horas. La copia no incluye logs ni trazas. Restaurar esa copia vuelve a dejar consultables las métricas de esas 48 horas, pero no recupera muestras que el borde todavía tenía solo en el buffer de disco y no había compactado.
