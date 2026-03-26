/** Estimate Pi using Monte Carlo simulation with error analysis. */

import java.util.Random;

public class Pi {
    static final Random rng = new Random(42);

    static double estimatePi(int nSamples) {
        int inside = 0;
        for (int i = 0; i < nSamples; i++) {
            double x = rng.nextDouble();
            double y = rng.nextDouble();
            if (x * x + y * y <= 1.0) {
                inside++;
            }
        }
        return 4.0 * inside / nSamples;
    }

    static double standardError(int nSamples, double piEstimate) {
        double p = piEstimate / 4.0;
        return 4.0 * Math.sqrt(p * (1 - p) / nSamples);
    }

    public static void main(String[] args) {
        int[] sampleSizes = {100, 1_000, 10_000, 100_000, 1_000_000};

        System.out.printf("%10s  %10s  %10s  %10s%n", "Samples", "Estimate", "Error", "Std Error");
        System.out.println("-".repeat(48));

        for (int n : sampleSizes) {
            double piHat = estimatePi(n);
            double se = standardError(n, piHat);
            double err = Math.abs(piHat - Math.PI);
            System.out.printf("%10d  %10.6f  %10.6f  %10.6f%n", n, piHat, err, se);
        }

        System.out.printf("%nTrue Pi: %.10f%n", Math.PI);
    }
}
