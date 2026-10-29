# Automatización de APIs – Billetera Digital (Karate + Maven)

Proyecto de automatización E2E sobre la Billetera Digital publicada en `http://134.209.211.10:5173/`.
La URL base es el frontend (Vite/React); los microservicios corren en el mismo host:

| Servicio            | Puerto | Base path            | Header `x-channel` |
|---------------------|--------|----------------------|--------------------|
| Auth Service        | 4001   | `/auth/v1`           | `POSTMAN`          |
| Wallet Service      | 4002   | `/wallet/v1`         | `POSTMAN`          |
| Transaction Service | 4003   | `/transaction/v1`    | `POSTMAN`          |
| Admin Service       | 4004   | `/admin/v1`          | `ADMIN`            |

## Requisitos

- JDK 17
- Maven 3.8+
- IntelliJ IDEA (plugin *Karate* opcional, para resaltado de sintaxis)

## Estructura

```
pom.xml
src/test/java/
├── karate-config.js              # URLs, timeouts, almacén global y generarCelular()
├── TestRunner.java               # JUnit 5, parallel(1), orden regression -> admin, genera PDF
├── utils/
│   ├── SharedStore.java          # Mapa estático que persiste datos entre escenarios/features
│   └── PdfReportGenerator.java   # Convierte los resultados de Karate en PDF
└── features/
    ├── regression.feature        # Escenarios 1, 2 y 3
    ├── admin.feature             # Feature 3: Flujo Administrador
    └── common/                   # Features reutilizables (@ignore)
        ├── login.feature
        ├── admin-login.feature
        └── asignar-saldo.feature
src/test/resources/logback-test.xml
tools/
└── generar_informe.py            # Arma el Informe de Ejecución (HTML + PDF) desde target/karate-reports
docs/
├── Informe-de-Ejecucion.pdf      # Informe para entregar
├── Informe-de-Ejecucion.html     # Fuente del PDF
├── evidencias/                   # Capturas del reporte HTML de Karate
└── Guion-Video.md
```

## Cómo se comparten los datos entre escenarios

Karate aísla las variables de cada `Scenario`. Para encadenar el flujo, `karate-config.js` expone
un objeto `store` (respaldado por `utils.SharedStore`) con `store.put(clave, valor)`,
`store.get(clave)` y `store.has(clave)`. Los valores se serializan a JSON para no compartir
objetos JS entre contextos. Por eso la suite se ejecuta con **un solo hilo** (`parallel(1)`) y
el `TestRunner` fija el orden de los features.

| Clave                  | La escribe   | La leen                 |
|------------------------|--------------|-------------------------|
| `emisor`, `receptor`   | Escenario 1  | Escenarios 2, 3 y admin |
| `saldoInicialEmisor`   | Escenario 1  | Escenario 2             |
| `saldoInicialReceptor` | Escenario 1  | Escenario 3             |
| `transactionId`        | Escenario 2  | Escenario 3             |
| `codigoTransaccion`    | Escenario 2  | Escenario 3 y admin     |
| `saldoFinalEmisor`     | Escenario 2  | admin                   |
| `saldoFinalReceptor`   | Escenario 3  | admin                   |

## Comandos (terminal integrada de IntelliJ)

Ejecutar toda la suite (regresión + admin) y generar reportes HTML y PDF:

```bash
mvn clean test
```

Si Maven falla descargando dependencias con `PKIX path building failed` (proxy o antivirus que
inspecciona HTTPS), usa el almacén de certificados de Windows. En PowerShell:

```powershell
$env:MAVEN_OPTS="-Djavax.net.ssl.trustStoreType=Windows-ROOT"; mvn clean test
```

Apuntar a otra URL base o a otras credenciales de administrador:

```bash
mvn clean test -Dbase.url=http://134.209.211.10:5173/ -Dadmin.user=admin -Dadmin.password=superpassword
```

Ejecutar un escenario puntual por tag (útil para depurar; los escenarios 2, 3 y admin dependen del 1):

```bash
mvn clean test -Dkarate.options="--tags @escenario1"
```

Abrir el reporte HTML de Karate (Windows):

```bash
start target/karate-reports/karate-summary.html
```

## Reportes generados

| Archivo                                             | Contenido                                              |
|-----------------------------------------------------|--------------------------------------------------------|
| `target/karate-reports/karate-summary.html`         | Reporte HTML nativo de Karate (request/response)       |
| `target/karate-reports/reporte-ejecucion.pdf`       | Resumen PDF: totales, escenarios y pasos con su estado |
| `target/karate-reports/*.json`                      | Cucumber JSON (para Jenkins/Allure/Xray)               |
| `target/karate.log`                                 | Log de la ejecución                                    |

## Informe de Ejecución

`docs/Informe-de-Ejecucion.pdf` contiene presentación, resumen, resultado por escenario, evidencia
HTTP (request/response) de cada escenario, capturas del reporte de Karate, hallazgos y conclusiones.
Se genera a partir de la última ejecución (requiere Python 3 y Chrome o Edge):

```bash
mvn clean test
```

```bash
python tools/generar_informe.py
```
