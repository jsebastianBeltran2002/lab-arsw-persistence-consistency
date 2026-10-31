# Evidencias · ARSW-EQP-03

## Entorno
macOS 26.6.2, Apple M5 con 10 núcleos disponibles para Docker, 16 GB de RAM en el equipo y unos 7,75 GB asignados a Docker. Docker Engine 29.6.1 y Docker Compose v5.3.0.

Todas las horas son del 31 de octubre de 2026 en UTC. La hora de Colombia es UTC menos 5, y las capturas de Grafana muestran hora local, por ejemplo 12:50 UTC son las 07:50.

## Registro
| Experimento | Inicio / fin y zona horaria | Archivo / captura | Resultado observado | Interpretación |
|---|---|---|---|---|
| Smoke | 12:48:15 UTC | smoke-20261031T124815012825Z.json | Arranque en true, versión 1 | Todo el entorno quedó arriba y el frontend llega a las dos APIs |
| Baseline | 12:48:24 a 12:48:47 UTC | baseline-20261031T124847048088Z.json | Ediciones concurrentes con 200 y 200, la versión pasó de 1 a 3. Luis revocado pudo escribir con 200. La presencia de Ana seguía después de 22 s | Se pierde una edición porque no se compara la versión, la caché autoriza escrituras y la clave de presencia no tiene TTL |
| Redis detenido en la base | 12:48:52 a 12:48:53 UTC | redis-down-BASE-20261031T124853Z.json | Edición 200 y presencia 503 | La presencia, que es opcional, fallaba en lugar de degradarse |
| Autoridad detenida en la base | 12:49:00 a 12:49:01 UTC | authority-down-BASE-20261031T124900Z.json | Edición 200 con Gestión apagada | La caché ocultaba la caída de Gestión y se aceptó una escritura sin validar el permiso |
| Restricciones SQL y rollback | 12:48:21 UTC | sql-restricciones.txt e inspeccion-datos.txt | Dentro de la transacción Luis queda sin permiso y después del ROLLBACK vuelve a tenerlo. Error de llave duplicada al repetir la membresía de Ana. Error de llave foránea con un usuario que no existe | La llave primaria compuesta impide dos membresías contradictorias para el mismo usuario y tablero. La llave foránea impide membresías de usuarios o tableros que no existen. La transacción hace que un cambio de permiso se aplique completo o no se aplique |
| Dos pestañas | 12:51:52 UTC con curl y cerca de las 13:00 UTC en el navegador | experimento1-dos-pestanas.txt, exp1-pestana1-200.png y exp1-pestana2-409.png | Las dos pestañas leen la versión 1. Ana guarda con 200 y queda versión 2. Luis recibe 409 y se le pide recargar. Queda guardada la edición de Ana | El 409 es un rechazo correcto del negocio. El servidor sigue funcionando y protege la edición que ya estaba guardada, no es un error 5xx |
| Acceptance corregido | 12:51:20 a 12:51:42 UTC y 12:52:58 a 12:53:20 UTC | acceptance-20261031T125142813562Z.json y acceptance-20261031T125320621329Z.json | Las 4 pruebas en true y código de salida 0. Ediciones con 200 y 409 y la versión sube una sola vez. Luis revocado recibe 403 aunque la caché decía que podía editar. La presencia desaparece a los 22 s | Los tres TODO cumplen los contratos del laboratorio |
| Redis detenido y recuperación | 12:51:52 a 12:52:25 UTC | redis-down-20261031T125205085504Z.json y paneles de dependencias y presencia degradada | Edición 200 y presencia 200 con available en false. Se mandaron 10 heartbeats más, todos degradados. Al iniciar Redis respondió PONG y el acceptance siguiente pasó | La presencia se degrada de forma controlada y el contenido sigue funcionando. La dependencia Redis bajó a 0 mientras los servicios seguían con up en 1 |
| Autoridad detenida y recuperación | 12:52:40 a 12:52:50 UTC | authority-down-20261031T125249389900Z.json | Con el permiso de Ana guardado en caché, la edición respondió 503 porque no se pudo validar el permiso. La consulta de permiso de la interfaz seguía diciendo que sí. Gestión volvió a quedar sana y el acceptance final pasó | La escritura deja de estar disponible a propósito: sin la fuente oficial no se acepta un permiso viejo. La caché sirve para la interfaz pero no autoriza |
| Carga k6 en la base | 12:49:14 a 12:51:03 UTC | k6-carga-summary-base.json | 1976 solicitudes, 19,7 por segundo, P95 de 9,34 ms, 0 % de fallos y 0 errores de contenido | Línea base de lecturas |
| Carga k6 con la solución | 12:53:26 a 12:55:07 UTC | k6-carga-summary-solucion.json | 1979 solicitudes, 19,8 por segundo, P95 de 9,25 ms, 0 % de fallos y 0 errores de contenido | No hay diferencia porque k6 solo lee y los cambios afectan escrituras y presencia. Esta carga no mide el costo de validar el permiso en cada escritura |

Los archivos del registro están en la carpeta entrega/evidencias. Los puntos crudos de k6 se generaron en results pero no se subieron por su tamaño.

## Observabilidad
El dashboard se llama ARSW-EQP-03 · Persistencia y está en la carpeta ARSW de Grafana. Tiene los 2 paneles iniciales, los 6 pedidos y uno opcional con las respuestas por código. Está exportado en entrega/dashboard.json y hay una captura con la ventana de los últimos 45 minutos en grafana-dashboard.png. La captura de los targets de Prometheus está en prometheus-targets.png.

En el dashboard se ven dos picos de unas 24 solicitudes por segundo que corresponden a las dos cargas de k6, entre las 07:49 y 07:51 y entre las 07:53 y 07:55 hora local. El P95 del backend estuvo entre 5 y 25 ms durante la carga, con un pico de unos 180 ms al inicio cuando había pocos datos en la ventana. El panel de dependencias muestra Redis en rojo dos veces, una por la prueba con el código base y otra con el código corregido. Los conflictos suben en cada acceptance y en la prueba de las dos pestañas. La presencia degradada solo sube con Redis caído y el código corregido, porque antes respondía 503 y no se contaba. Los errores 5xx quedan casi en 0 y el único 503 fue el esperado en la prueba de autoridad caída.

¿Por qué puede subir el contador de conflictos mientras baja la pérdida de cambios?
Porque cada conflicto es un cambio que no se perdió. Antes la segunda escritura sobrescribía la primera sin avisar, las dos respondían 200 y el contador quedaba en 0. Ahora la escritura con versión vieja se rechaza con 409 y se cuenta. Que haya más conflictos significa que el sistema detecta algo que antes pasaba sin que nadie lo notara.

¿Por qué el panel de caché no demuestra que una escritura fue autorizada correctamente?
Ese panel solo cuenta aciertos y fallos de la caché que usa la interfaz, y las escrituras ya no pasan por ella sino por Gestión. Una caché con 100 % de aciertos puede estar entregando un permiso que ya fue revocado, como vimos cuando Gestión estaba apagada y la caché seguía diciendo que Ana podía editar. Que la autorización sea correcta se comprueba con las pruebas de acceptance, que dan 403 después de revocar y 503 sin autoridad.

¿Qué ve Grafana cuando Redis cae, pero la API sigue contestando 200?
El panel de up sigue en 1 porque Prometheus puede leer las métricas del servicio, y las solicitudes por segundo y los 5xx no cambian. Lo que cambia es que la dependencia de Redis pasa a 0 y el contador de presencia degradada sube, porque las respuestas son 200 pero con la presencia no disponible. El servicio sigue respondiendo pero con menos funcionalidad, y eso solo se ve en esos dos paneles.

¿Por qué el P95 de k6 y el P95 del backend no tienen necesariamente el mismo valor?
k6 mide todo el recorrido desde el cliente, incluyendo la red de Docker y el paso por Nginx, y calcula el percentil con todas las solicitudes reales de la prueba. El backend mide solo el tiempo dentro de la aplicación, y Prometheus estima el P95 a partir de buckets de un histograma en ventanas de un minuto, mezclado con otras solicitudes como los sondeos. Miden cosas distintas, en ventanas distintas y con distinta precisión.

## Problemas pendientes
- La carrera entre validar el permiso y escribir no se resolvió porque el laboratorio no lo pide. Está explicada en la sección de consecuencias del ADR.
- En el panel de dependencias no se alcanza a ver la caída de Gestión, que duró entre 8 y 10 segundos. El sondeo corre cada 5 segundos y Prometheus muestrea con su propio intervalo, así que una parada tan corta puede no quedar registrada. La evidencia de esa prueba es el JSON de authority-down.
- No ejecutamos las pruebas opcionales de estrés, pico y resistencia.
