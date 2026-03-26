"""Estimate Pi using Monte Carlo simulation with error analysis."""

import math
import random

random.seed(42)

def estimate_pi(n_samples):
    inside = 0
    for _ in range(n_samples):
        x = random.random()
        y = random.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return 4.0 * inside / n_samples

def standard_error(n_samples, pi_estimate):
    p = pi_estimate / 4.0
    return 4.0 * math.sqrt(p * (1 - p) / n_samples)

sample_sizes = [100, 1_000, 10_000, 100_000, 1_000_000]

print(f"{'Samples':>10s}  {'Estimate':>10s}  {'Error':>10s}  {'Std Error':>10s}")
print("-" * 48)

for n in sample_sizes:
    pi_hat = estimate_pi(n)
    se = standard_error(n, pi_hat)
    err = abs(pi_hat - math.pi)
    print(f"{n:>10,d}  {pi_hat:>10.6f}  {err:>10.6f}  {se:>10.6f}")

print(f"\nTrue Pi: {math.pi:.10f}")
