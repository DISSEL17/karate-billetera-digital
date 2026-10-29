# Guion del video explicativo (≈ 2 minutos)

Se evalúa: narración, tiempo de ejecución, secuencia, explicación y que se muestre el reporte PDF generado.
Truco de tiempo: lanza `mvn clean test` al inicio; tarda ~25 s y lo explicas mientras corre.
Los tiempos son acumulados (~140 palabras por minuto).

---

### 0:00 – 0:12 · Presentación
**En pantalla:** IntelliJ con el proyecto abierto.

> "Hola, soy Jonathan Castañeda. Presento la automatización de las APIs de la Billetera Digital con Karate, Maven y JUnit 5: registro de usuarios, una transferencia y su validación, incluida la auditoría del administrador."

### 0:12 – 0:22 · Lanzar la ejecución
**En pantalla:** terminal de IntelliJ, escribir y ejecutar `mvn clean test`.

> "Lanzo la suite con mvn clean test. Mientras se ejecuta, les explico cómo está armada."

### 0:22 – 0:45 · Arquitectura (mientras corre)
**En pantalla:** `karate-config.js` → `TestRunner.java`.

> "En karate-config definí las URLs de los cuatro microservicios, los timeouts, la función generarCelular, que crea teléfonos únicos en cada corrida, y un almacén global llamado store. Karate aísla cada escenario; store me permite pasar usuarios, saldos y el código de transacción entre ellos. Por eso el TestRunner ejecuta con parallel de uno y en orden: primero regresión y luego admin."

### 0:45 – 1:15 · Los escenarios
**En pantalla:** `regression.feature`, luego `admin.feature`.

> "Escenario uno: registro un emisor y un receptor, valido el esquema con matchers, pruebo que un registro duplicado devuelva 409 y les asigno dos mil de saldo, verificándolo con el token de cada uno.
> Escenario dos: el emisor inicia sesión, transfiere cuatrocientos cincuenta con la nota 'Pago de Servicios', valido la respuesta con una tabla de aserciones y compruebo que su saldo bajó exactamente cuatrocientos cincuenta.
> Escenario tres: el receptor ve el aumento y encuentra la transacción en su historial.
> Y en el feature de administrador, el admin encuentra el débito y el crédito en la auditoría, confirma los saldos y se valida que sin permisos responda 401 y 403."

### 1:15 – 1:30 · Resultado
**En pantalla:** volver a la terminal: `scenarios: 8 | passed: 8 | failed: 0` y `BUILD SUCCESS`.

> "La ejecución terminó en unos veinte segundos: ocho escenarios, ocho aprobados, cero fallidos."

### 1:30 – 1:48 · Reportes PDF
**En pantalla:** `target/karate-reports/karate-summary.html` → `target/karate-reports/reporte-ejecucion.pdf` → `docs/Informe-de-Ejecucion.pdf` (pasar por resumen, evidencia y hallazgos).

> "Karate genera su reporte HTML con cada petición y respuesta, y el runner produce este reporte PDF. Con esos resultados armé el informe de ejecución: resumen, resultado y evidencia por escenario, hallazgos y conclusiones."

### 1:48 – 2:00 · Hallazgos y cierre

> "Encontré seis hallazgos; los más importantes: el PIN viaja en texto plano y el transactionId no aparece en el historial, así que la trazabilidad depende del código de referencia. El código está en el repositorio de Git, rama main. Gracias."

---

## Checklist de grabación

- [ ] Ejecutar `mvn clean test` una vez antes de grabar, para que las dependencias ya estén descargadas.
- [ ] Si Maven da error PKIX, define antes `$env:MAVEN_OPTS="-Djavax.net.ssl.trustStoreType=Windows-ROOT"` en la terminal.
- [ ] Fuente del editor y de la terminal en 16 pt o más.
- [ ] Cerrar notificaciones y pestañas que no se usen.
- [ ] Tener a mano `karate-summary.html`, `reporte-ejecucion.pdf` e `Informe-de-Ejecucion.pdf`.
- [ ] Grabar en 1080p (Win + Alt + R con la Xbox Game Bar, u OBS) y revisar el audio.
- [ ] Subir a Google Drive → Compartir → "Cualquier persona con el enlace" → Lector, y copiar la URL.
