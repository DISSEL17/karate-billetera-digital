import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import org.junit.jupiter.api.Test;
import utils.PdfReportGenerator;
import utils.SharedStore;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TestRunner {

    private static final String REPORT_DIR = "target/karate-reports";

    @Test
    void ejecutarRegresion() {
        SharedStore.clear();

        // Orden explicito: regression.feature produce los datos que admin.feature valida.
        Results results = Runner
                .path("classpath:features/regression.feature",
                      "classpath:features/admin.feature")
                .outputHtmlReport(true)
                .outputCucumberJson(true)
                .reportDir(REPORT_DIR)
                .parallel(1);

        PdfReportGenerator.generate(results, REPORT_DIR + "/reporte-ejecucion.pdf");

        assertEquals(0, results.getFailCount(), results.getErrorMessages());
    }
}
