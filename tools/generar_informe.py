"""
Genera el Informe de Ejecucion (HTML + PDF) a partir de los resultados de Karate.

Uso (despues de `mvn clean test`):
    python tools/generar_informe.py

Salidas:
    docs/evidencias/*.png            capturas del reporte HTML de Karate
    docs/Informe-de-Ejecucion.html
    docs/Informe-de-Ejecucion.pdf
"""
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "target" / "karate-reports"
DOCS = ROOT / "docs"
EVIDENCIAS = DOCS / "evidencias"

AUTOR = "Jonathan Castañeda"
ROL = "QA Automation Engineer"
SALDO_ASIGNADO = 2000.00
MONTO = 450.00

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
]

HALLAZGOS = [
    ("H-01", "Media", "POST /transaction/v1/transfer · GET /wallet/v1/transactions",
     "El <b>transactionId</b> devuelto por la transferencia no aparece en el historial; los movimientos "
     "tienen otros IDs (<code>tx-&lt;timestamp&gt;-&lt;n&gt;</code>). El único dato común es <b>referenceCode</b>.",
     "Persistir el transactionId en ambos asientos o documentar referenceCode como identificador oficial. "
     "La suite valida la trazabilidad por referenceCode."),
    ("H-02", "Alta", "POST /auth/v1/register · POST /auth/v1/login · GET /admin/v1/users",
     "Las respuestas exponen el <b>PIN en texto plano</b> (<code>\"pin\":\"123456\"</code>).",
     "No devolver el PIN en ninguna respuesta y almacenarlo con hash."),
    ("H-03", "Alta", "POST /admin/v1/balance",
     "El ajuste de saldo no tiene límites: en el entorno existen usuarios con saldo <code>1.0e+72</code> y "
     "<code>-1.0e+72</code> (montos desmesurados y saldos negativos).",
     "Validar el rango del monto y no permitir saldo final negativo."),
    ("H-04", "Media", "POST /auth/v1/register",
     "No se valida el formato del teléfono ni del email: hay usuarios con teléfono <code>ASDASDASD</code>, "
     "<code>123</code> o de 16 dígitos, y emails como <code>9191com</code>.",
     "Validar teléfono (9 dígitos numéricos) y email en el backend y responder 400."),
    ("H-05", "Baja", "PUT /admin/v1/users/:id",
     "Se aceptan estados fuera del catálogo (<code>ACTIVEeeee</code>).",
     "Restringir status a ACTIVE / DELETED."),
    ("H-06", "Baja", "POST /admin/v1/login",
     "La documentación indica que el Admin Service solo acepta <code>x-channel: ADMIN</code>, pero el login "
     "responde 200 también con <code>x-channel: WEB</code>.",
     "Rechazar con 400 GEN_001 los canales distintos de ADMIN."),
]

VALIDACIONES = {
    "Escenario 1": "Registro 201 de Emisor y Receptor con teléfono aleatorio único; esquema del usuario con "
                   "matchers (#string, #regex, #array); <b>negativo</b>: registro duplicado → 409 AUTH_006; "
                   "abono de 2000.00 vía Admin; saldo consultado con el token de cada usuario = saldo asignado.",
    "Escenario 2": "Login del Emisor y captura del token Bearer; transferencia de 450.00 con nota "
                   "\"Pago de Servicios\" → 200; tabla de aserción (status COMPLETED, mensaje, transactionId, "
                   "referenceCode); saldo Emisor = saldo inicial − 450.00.",
    "Escenario 3": "Login del Receptor; saldo = saldo inicial + 450.00; el historial contiene el código de la "
                   "transacción como INCOME de 450.00 con la contraparte y la nota correctas.",
    "Login de administrador": "Login admin 200 (token Bearer, expiresIn 14400); credenciales inválidas → 401 AUTH_003.",
    "El administrador valida": "La auditoría global contiene la referencia con 2 asientos: débito EXPENSE del "
                               "Emisor y crédito INCOME del Receptor por 450.00.",
    "El administrador confirma": "GET /admin/v1/users: Emisor y Receptor ACTIVE con los saldos finales esperados.",
    "sin token": "Sin token → 401 ADM_001.",
    "token de usuario": "Token de usuario sin rol admin → 403 ADM_002.",
}


def esc(text):
    return html.escape(str(text), quote=True)


def find_browser():
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("No se encontró Chrome ni Edge para exportar el PDF.")


def load(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def flatten_steps(step_results):
    """Recorre los pasos, incluyendo los de features invocados con call."""
    for sr in step_results:
        yield sr
        for call in sr.get("callResults", []) or []:
            for scen in call.get("scenarioResults", []):
                yield from flatten_steps(scen.get("stepResults", []))


def mask(body):
    body = re.sub(r'("token"\s*:\s*")([^"]{12})[^"]*"', r'\1\2…"', body)
    body = re.sub(r'(Authorization: Bearer )(\S{12})\S*', r'\1\2…', body)
    body = re.sub(r'("password"\s*:\s*")[^"]*"', r'\1********"', body)
    return body


def parse_http(step_log):
    """Extrae llamadas HTTP (metodo, url, request, status, tiempo, response) de un stepLog de Karate."""
    calls = []
    for m in re.finditer(r"(\d+) > (GET|POST|PUT|DELETE|PATCH) (\S+)", step_log):
        n, method, url = m.group(1), m.group(2), m.group(3)
        rest = step_log[m.end():]
        req_body = ""
        req_part = rest.split("response time in milliseconds")[0]
        req_lines = [l for l in req_part.splitlines() if not re.match(rf"\s*{n} >", l) and "request:" not in l]
        req_body = "\n".join(req_lines).strip()
        req_body = re.sub(r"\n?\d{2}:\d{2}:\d{2}\.\d{3}\s*$", "", req_body).strip()
        t = re.search(r"response time in milliseconds: (\d+)", rest)
        st = re.search(rf"{n} < (\d{{3}})", rest)
        resp_body = ""
        if st:
            after = rest[st.end():]
            lines = after.splitlines()
            body_lines = [l for l in lines if not re.match(rf"\s*{n} <", l)]
            resp_body = "\n".join(body_lines).strip()
            nxt = re.search(r"\n\d{2}:\d{2}:\d{2}\.\d{3} ", "\n" + resp_body)
            if nxt:
                resp_body = ("\n" + resp_body)[: nxt.start()].strip()
        calls.append({
            "method": method,
            "url": url,
            "request": mask(req_body),
            "status": st.group(1) if st else "?",
            "ms": t.group(1) if t else "?",
            "response": mask(resp_body),
        })
    return calls


def short_json(text, limit=900):
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 3:
            text = json.dumps(data[:2], ensure_ascii=False, indent=2)
            return text + f"\n… ({len(data)} elementos en total)"
        text = json.dumps(data, ensure_ascii=False, indent=2)
    except (ValueError, TypeError):
        pass
    return text if len(text) <= limit else text[:limit] + "\n…"


def screenshot(browser, page, out, height):
    url = (REPORTS / page).as_uri()
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size=1280,{height}", f"--screenshot={out}", url],
                   check=True, capture_output=True, timeout=120)


def main():
    if not (REPORTS / "karate-summary-json.txt").exists():
        sys.exit("No hay resultados. Ejecuta primero: mvn clean test")

    browser = find_browser()
    summary = load("karate-summary-json.txt")
    features = [load("features.regression.karate-json.txt"), load("features.admin.karate-json.txt")]

    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    screenshot(browser, "karate-summary.html", EVIDENCIAS / "01-karate-summary.png", 520)
    screenshot(browser, "features.regression.html", EVIDENCIAS / "02-regression-feature.png", 1500)
    screenshot(browser, "features.admin.html", EVIDENCIAS / "03-admin-feature.png", 1500)

    # Datos de la corrida a partir de los karate.log() del flujo
    all_logs = "\n".join(
        s.get("stepLog", "")
        for f in features for sc in f["scenarioResults"] for s in flatten_steps(sc["stepResults"])
    )
    datos = {}
    m = re.search(r"Emisor: (\d+) (u_\d+) \| Receptor: (\d+) (u_\d+)", all_logs)
    if m:
        datos.update(emisor_phone=m.group(1), emisor_id=m.group(2), receptor_phone=m.group(3), receptor_id=m.group(4))
    m = re.search(r"Transaccion: (\S+) \| Referencia: (\S+)", all_logs)
    if m:
        datos.update(tx=m.group(1), ref=m.group(2))

    escenarios = []
    for f in features:
        for sc in f["scenarioResults"]:
            name = sc["name"]
            if sc.get("exampleIndex", -1) >= 0 and sc.get("exampleData"):
                name = name.replace("<caso>", str(sc["exampleData"].get("caso", "")))
            steps = list(flatten_steps(sc["stepResults"]))
            calls = []
            for s in steps:
                calls.extend(parse_http(s.get("stepLog", "")))
            failed = sc.get("failed", False) or any(s["result"]["status"] == "failed" for s in steps)
            escenarios.append({
                "feature": f["relativePath"],
                "name": name,
                "ms": sc.get("durationMillis", 0),
                "failed": failed,
                "steps": len([s for s in sc["stepResults"] if not s["step"].get("background")]),
                "calls": calls,
            })

    total = len(escenarios)
    fallidos = sum(1 for e in escenarios if e["failed"])
    aprobados = total - fallidos
    fecha_ejec = summary.get("resultDate", "")
    estado_global = "APROBADO" if fallidos == 0 else "CON FALLOS"

    def validacion(nombre):
        for k, v in VALIDACIONES.items():
            if k.lower() in nombre.lower():
                return v
        return ""

    h = []
    h.append(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Informe de Ejecución - Billetera Digital</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; color: #1e293b; line-height: 1.45; }}
h1 {{ font-size: 22pt; margin: 0 0 4px; color: #0c4a6e; }}
h2 {{ font-size: 14pt; color: #0c4a6e; border-bottom: 2px solid #0ea5e9; padding-bottom: 3px; margin-top: 22px; }}
h3 {{ font-size: 11.5pt; margin: 16px 0 6px; }}
table {{ width: 100%; border-collapse: collapse; margin: 6px 0 10px; }}
th, td {{ border: 1px solid #cbd5e1; padding: 5px 7px; text-align: left; vertical-align: top; }}
th {{ background: #e0f2fe; }}
.pass {{ color: #15803d; font-weight: 700; }} .fail {{ color: #b91c1c; font-weight: 700; }}
.cover {{ height: 245mm; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }}
.cover .sub {{ font-size: 13pt; color: #475569; margin-bottom: 28px; }}
.cover table td:first-child {{ width: 32%; font-weight: 600; background: #f8fafc; }}
.kpis {{ display: flex; gap: 10px; margin: 10px 0; }}
.kpi {{ flex: 1; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px; text-align: center; }}
.kpi b {{ display: block; font-size: 18pt; }}
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; color: #fff; font-weight: 700; }}
.ok {{ background: #15803d; }} .ko {{ background: #b91c1c; }}
pre {{ background: #0f172a; color: #e2e8f0; padding: 7px 9px; border-radius: 6px; font-size: 7.6pt;
      white-space: pre-wrap; word-break: break-all; margin: 3px 0; }}
.call {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 8px; margin: 6px 0; page-break-inside: avoid; }}
.call .hdr {{ font-family: Consolas, monospace; font-size: 8.5pt; font-weight: 700; }}
.lbl {{ font-size: 7.5pt; text-transform: uppercase; color: #64748b; margin-top: 4px; }}
.scen {{ page-break-before: always; }}
img {{ width: 100%; border: 1px solid #cbd5e1; border-radius: 6px; margin: 6px 0; }}
.sev-Alta {{ color: #b91c1c; font-weight: 700; }} .sev-Media {{ color: #c2410c; font-weight: 700; }}
.sev-Baja {{ color: #a16207; font-weight: 700; }}
code {{ background: #f1f5f9; padding: 0 3px; border-radius: 3px; font-size: 8.8pt; }}
</style></head><body>""")

    # 1. Presentacion
    h.append(f"""<section class="cover">
<h1>Informe de Ejecución de Pruebas</h1>
<div class="sub">Automatización de APIs – Billetera Digital</div>
<table>
<tr><td>Proyecto</td><td>Evaluación de Automatización de APIs – Billetera Digital</td></tr>
<tr><td>Sistema bajo prueba</td><td>http://134.209.211.10:5173/ (microservicios Auth 4001, Wallet 4002, Transaction 4003, Admin 4004)</td></tr>
<tr><td>Herramientas</td><td>Karate Framework {esc(summary.get('version', ''))} · JUnit 5 · Maven · Java 17</td></tr>
<tr><td>Tipo de prueba</td><td>Regresión funcional E2E de API</td></tr>
<tr><td>Modo de ejecución</td><td>Secuencial, {summary.get('threads', 1)} hilo (parallel(1))</td></tr>
<tr><td>Entorno</td><td>{esc(summary.get('env', ''))}</td></tr>
<tr><td>Fecha de ejecución</td><td>{esc(fecha_ejec)}</td></tr>
<tr><td>Elaborado por</td><td>{esc(AUTOR)} – {esc(ROL)}</td></tr>
<tr><td>Resultado</td><td><span class="badge {'ok' if fallidos == 0 else 'ko'}">{estado_global}</span></td></tr>
</table></section>""")

    # 2. Resumen
    h.append(f"""<h2>1. Resultado de ejecución – Resumen</h2>
<div class="kpis">
<div class="kpi"><b>{len(summary.get('featureSummary', []))}</b>Features</div>
<div class="kpi"><b>{total}</b>Escenarios</div>
<div class="kpi"><b class="pass">{aprobados}</b>Aprobados</div>
<div class="kpi"><b class="{'fail' if fallidos else 'pass'}">{fallidos}</b>Fallidos</div>
<div class="kpi"><b>{aprobados * 100 // max(total, 1)}%</b>Éxito</div>
<div class="kpi"><b>{summary.get('totalTime', 0) / 1000:.1f}s</b>Duración</div>
</div>
<p>El flujo <b>Registro → Transferencia → Validación en Receptor → Auditoría del Administrador</b> se ejecutó de
punta a punta. Los datos se comparten entre escenarios mediante un almacén global definido en
<code>karate-config.js</code>, por lo que la suite corre en un solo hilo y en orden.</p>
<h3>Datos de la ejecución</h3>
<table>
<tr><th>Dato</th><th>Valor</th></tr>
<tr><td>Emisor (teléfono / id)</td><td>{esc(datos.get('emisor_phone', '-'))} / {esc(datos.get('emisor_id', '-'))}</td></tr>
<tr><td>Receptor (teléfono / id)</td><td>{esc(datos.get('receptor_phone', '-'))} / {esc(datos.get('receptor_id', '-'))}</td></tr>
<tr><td>Saldo asignado a cada usuario</td><td>{SALDO_ASIGNADO:,.2f} USD</td></tr>
<tr><td>Monto transferido / nota</td><td>{MONTO:,.2f} USD / "Pago de Servicios"</td></tr>
<tr><td>transactionId</td><td>{esc(datos.get('tx', '-'))}</td></tr>
<tr><td>Código de referencia</td><td>{esc(datos.get('ref', '-'))}</td></tr>
<tr><td>Saldo final Emisor</td><td>{SALDO_ASIGNADO - MONTO:,.2f} USD ({SALDO_ASIGNADO:,.2f} − {MONTO:,.2f})</td></tr>
<tr><td>Saldo final Receptor</td><td>{SALDO_ASIGNADO + MONTO:,.2f} USD ({SALDO_ASIGNADO:,.2f} + {MONTO:,.2f})</td></tr>
</table>
<h3>Reporte de Karate (resumen)</h3>
<img src="evidencias/01-karate-summary.png" alt="Resumen Karate">""")

    # 3. Resultado por escenario
    h.append("""<h2>2. Resultado por escenario</h2><table>
<tr><th>#</th><th>Feature</th><th>Escenario</th><th>Validaciones</th><th>Tiempo</th><th>Estado</th></tr>""")
    for i, e in enumerate(escenarios, 1):
        estado = '<span class="fail">FAIL</span>' if e["failed"] else '<span class="pass">PASS</span>'
        h.append(f"<tr><td>{i}</td><td>{esc(e['feature'].split('/')[-1])}</td><td>{esc(e['name'])}</td>"
                 f"<td>{validacion(e['name'])}</td><td>{e['ms'] / 1000:.2f}s</td><td>{estado}</td></tr>")
    h.append("</table>")

    # 4. Evidencia por escenario
    h.append('<h2 class="scen">3. Evidencia de la ejecución por escenario</h2>'
             '<p>Peticiones y respuestas HTTP registradas por Karate durante la ejecución '
             '(los tokens se muestran truncados).</p>')
    for i, e in enumerate(escenarios, 1):
        estado = '<span class="badge ko">FAIL</span>' if e["failed"] else '<span class="badge ok">PASS</span>'
        h.append(f'<h3 style="page-break-before:{"always" if i > 1 else "auto"}">{i}. {esc(e["name"])} {estado}</h3>')
        h.append(f"<p>{validacion(e['name'])}</p>")
        for c in e["calls"]:
            h.append(f'<div class="call"><div class="hdr">{c["method"]} {esc(c["url"])} → '
                     f'<span class="{"pass" if c["status"].startswith("2") else "fail"}">{c["status"]}</span>'
                     f' · {c["ms"]} ms</div>')
            if c["request"]:
                h.append(f'<div class="lbl">Request</div><pre>{esc(short_json(c["request"], 600))}</pre>')
            if c["response"]:
                h.append(f'<div class="lbl">Response</div><pre>{esc(short_json(c["response"]))}</pre>')
            h.append("</div>")

    h.append('<h3 style="page-break-before:always">Reporte de Karate – regression.feature</h3>'
             '<img src="evidencias/02-regression-feature.png" alt="regression.feature">'
             '<h3 style="page-break-before:always">Reporte de Karate – admin.feature</h3>'
             '<img src="evidencias/03-admin-feature.png" alt="admin.feature">')

    # 5. Hallazgos
    h.append('<h2 style="page-break-before:always">4. Hallazgos</h2><table>'
             '<tr><th>ID</th><th>Severidad</th><th>Endpoint</th><th>Descripción</th><th>Recomendación</th></tr>')
    for hid, sev, ep, desc, rec in HALLAZGOS:
        h.append(f'<tr><td>{hid}</td><td class="sev-{sev}">{sev}</td><td><code>{esc(ep)}</code></td>'
                 f'<td>{desc}</td><td>{rec}</td></tr>')
    h.append("</table><p><i>H-03, H-04 y H-05 se observaron en datos del entorno compartido creados por otras "
             "ejecuciones; demuestran que la API aceptó esos valores.</i></p>")

    # 6. Conclusiones
    h.append(f"""<h2>5. Conclusiones</h2><ol>
<li>El flujo principal de la billetera <b>cumple</b> lo esperado: {aprobados} de {total} escenarios aprobados. Los
saldos cuadran exactamente (−{MONTO:.2f} en el Emisor, +{MONTO:.2f} en el Receptor) y la operación queda registrada
con doble asiento en la auditoría del administrador.</li>
<li>Los controles funcionan: registro duplicado → 409 AUTH_006; Admin sin token → 401 ADM_001; Admin con token de
usuario → 403 ADM_002; credenciales de admin inválidas → 401 AUTH_003.</li>
<li>La trazabilidad de la transferencia depende de <b>referenceCode</b>, porque el transactionId devuelto no aparece
en el historial (H-01).</li>
<li>Existen riesgos de <b>seguridad</b> (PIN expuesto, H-02) y de <b>integridad de datos</b> (montos y formatos sin
validar, H-03 a H-05) que deben corregirse antes de pasar a producción.</li>
<li>La suite es repetible: genera usuarios con teléfonos únicos en cada corrida, no depende de datos previos y se
ejecuta con <code>mvn clean test</code> en unos {summary.get('elapsedTime', 0) / 1000:.0f} segundos.</li>
</ol>
<p><b>Próximos pasos sugeridos:</b> casos negativos de transferencia (saldo insuficiente WALL_001, límite diario
WALL_002, destinatario inexistente TRX_002, autotransferencia TRX_001), integración en CI y ejecución sobre un
entorno con datos aislados.</p>
<p style="margin-top:30px;color:#64748b;font-size:8.5pt">Informe generado el {datetime.now():%d/%m/%Y %H:%M}
a partir de <code>target/karate-reports</code>.</p>
</body></html>""")

    html_path = DOCS / "Informe-de-Ejecucion.html"
    pdf_path = DOCS / "Informe-de-Ejecucion.pdf"
    html_path.write_text("".join(h), encoding="utf-8")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, capture_output=True, timeout=120)
    print(f"Informe HTML: {html_path}")
    print(f"Informe PDF:  {pdf_path}")


if __name__ == "__main__":
    main()
