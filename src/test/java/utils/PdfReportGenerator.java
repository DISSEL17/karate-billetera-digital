package utils;

import com.intuit.karate.Results;
import com.intuit.karate.core.ScenarioResult;
import com.intuit.karate.core.StepResult;
import com.openhtmltopdf.pdfboxout.PdfRendererBuilder;
import com.openhtmltopdf.util.XRLog;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Convierte los resultados de Karate en un PDF (target/karate-reports/reporte-ejecucion.pdf).
 * El reporte HTML nativo de Karate se sigue generando en la misma carpeta.
 */
public final class PdfReportGenerator {

    private PdfReportGenerator() {
    }

    public static void generate(Results results, String outputPath) {
        try {
            XRLog.setLoggingEnabled(false);
            File out = new File(outputPath);
            out.getParentFile().mkdirs();
            try (OutputStream os = new FileOutputStream(out)) {
                PdfRendererBuilder builder = new PdfRendererBuilder();
                builder.useFastMode();
                builder.withHtmlContent(buildHtml(results), null);
                builder.toStream(os);
                builder.run();
            }
            System.out.println("Reporte PDF generado: " + out.getAbsolutePath());
        } catch (Exception e) {
            // El PDF es un entregable adicional: no debe ocultar el resultado de las pruebas.
            System.err.println("No se pudo generar el PDF: " + e.getMessage());
        }
    }

    private static String buildHtml(Results results) {
        List<ScenarioResult> scenarios = results.getScenarioResults().collect(Collectors.toList());
        int passed = results.getScenariosPassed();
        int failed = results.getScenariosFailed();
        String fecha = LocalDateTime.now().format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss"));

        StringBuilder html = new StringBuilder();
        html.append("<html><head><meta charset=\"UTF-8\"/><style>")
            .append("body{font-family:Helvetica,Arial,sans-serif;font-size:10pt;color:#1e293b;}")
            .append("h1{font-size:18pt;margin-bottom:2px;}h2{font-size:13pt;margin-top:18px;border-bottom:1px solid #cbd5e1;}")
            .append("table{width:100%;border-collapse:collapse;margin-top:6px;}")
            .append("th,td{border:1px solid #cbd5e1;padding:4px 6px;text-align:left;vertical-align:top;}")
            .append("th{background:#e2e8f0;}.ok{color:#15803d;font-weight:bold;}.ko{color:#b91c1c;font-weight:bold;}")
            .append(".skip{color:#64748b;}.mono{font-family:Courier,monospace;font-size:8.5pt;}")
            .append("</style></head><body>");

        html.append("<h1>Reporte de Ejecucion - Billetera Digital</h1>")
            .append("<div>Karate Framework | Generado: ").append(esc(fecha)).append("</div>");

        html.append("<h2>Resumen</h2><table>")
            .append("<tr><th>Features</th><th>Escenarios</th><th>Exitosos</th><th>Fallidos</th><th>Duracion (s)</th></tr>")
            .append("<tr><td>").append(results.getFeaturesTotal()).append("</td>")
            .append("<td>").append(passed + failed).append("</td>")
            .append("<td class=\"ok\">").append(passed).append("</td>")
            .append("<td class=\"").append(failed > 0 ? "ko" : "ok").append("\">").append(failed).append("</td>")
            .append("<td>").append(String.format("%.2f", results.getElapsedTime() / 1000)).append("</td></tr>")
            .append("</table>");

        html.append("<h2>Escenarios</h2><table>")
            .append("<tr><th>Feature</th><th>Escenario</th><th>Estado</th><th>Duracion (ms)</th></tr>");
        for (ScenarioResult sr : scenarios) {
            html.append("<tr><td>").append(esc(sr.getScenario().getFeature().getName())).append("</td>")
                .append("<td>").append(esc(sr.getScenario().getName())).append("</td>")
                .append(statusCell(sr.isFailed() ? "failed" : "passed"))
                .append("<td>").append(Math.round(sr.getDurationMillis())).append("</td></tr>");
        }
        html.append("</table>");

        for (ScenarioResult sr : scenarios) {
            html.append("<h2>").append(esc(sr.getScenario().getName())).append("</h2>")
                .append("<table><tr><th style=\"width:78%\">Paso</th><th>Estado</th></tr>");
            for (StepResult step : sr.getStepResults()) {
                if (step.isHidden()) {
                    continue;
                }
                html.append("<tr><td class=\"mono\">")
                    .append(esc(step.getStep().getPrefix() + " " + step.getStep().getText()))
                    .append("</td>")
                    .append(statusCell(step.getResult().getStatus()))
                    .append("</tr>");
            }
            html.append("</table>");
            if (sr.isFailed()) {
                html.append("<p class=\"ko mono\">").append(esc(sr.getErrorMessage())).append("</p>");
            }
        }

        html.append("</body></html>");
        return html.toString();
    }

    private static String statusCell(String status) {
        String css = "passed".equals(status) ? "ok" : "failed".equals(status) ? "ko" : "skip";
        return "<td class=\"" + css + "\">" + esc(status.toUpperCase()) + "</td>";
    }

    private static String esc(String text) {
        if (text == null) {
            return "";
        }
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
    }
}
