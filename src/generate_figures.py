"""Generate vector PDFs and a summary table from measured CSV, never mock values."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .chain import ROOT

# Table 1 columns fixed in the Stage 3 proposal, summarized by method, n and actual k.
TABLE_METRICS = ['issue_gas_per_credential', 'revoke_total_gas', 'revoke_mean_gas',
                 'verify_estimate_gas', 'proof_bytes']


def sample_std(values):
    """Sample standard deviation (n - 1 denominator); zero for a single value."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, default=ROOT / 'data/raw/benchmark.csv')
    p.add_argument('--output', type=Path, default=ROOT / 'figures')
    args = p.parse_args()
    with args.input.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError('empty benchmark CSV')
    plot_groups = defaultdict(list)
    for row in rows:
        plot_groups[(row['method'], int(row['batch_size']))].append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    for metric, label, filename, log in [
        ('issue_gas_per_credential', 'Issuance gas per credential (gas units)', 'issuance_scaling.pdf', True),
        ('verify_estimate_gas', 'Simulated verification transaction estimate (gas units)', 'verification_gas.pdf', False),
        ('verify_call_median_ms', 'Local EVM eth_call duration (ms)', 'local_call_latency.pdf', False)]:
        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        for method, title in [('individual', 'Individual registry'), ('merkle_batch', 'Merkle batch')]:
            sizes = sorted(n for m, n in plot_groups if m == method)
            values = [[float(r[metric]) for r in plot_groups[(method, n)]] for n in sizes]
            ax.errorbar(sizes, [statistics.mean(v) for v in values],
                        yerr=[sample_std(v) for v in values],
                        marker='o', capsize=3, label=title)
        ax.set_xscale('log', base=2)
        if log:
            ax.set_yscale('log')
        ax.set_xlabel('Credentials per issuance batch (count)')
        ax.set_ylabel(label)
        ax.grid(alpha=.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.output / filename)
        plt.close(fig)
    table_groups = defaultdict(list)
    for row in rows:
        table_groups[(row['method'], int(row['batch_size']), int(row['revoked_count']))].append(row)
    summary = []
    for (method, size, k), group in sorted(table_groups.items()):
        fractions = sorted({r['revocation_fraction'] for r in group}, key=float)
        record = {'method': method, 'batch_size': size, 'revoked_count': k,
                  'revocation_fractions': ';'.join(fractions), 'repeats': len(group)}
        for metric in TABLE_METRICS:
            if metric == 'revoke_mean_gas' and k == 0:
                # Gas per revocation is undefined when nothing was revoked.
                record[metric + '_mean'] = record[metric + '_std'] = ''
                continue
            values = [float(r[metric]) for r in group]
            record[metric + '_mean'] = round(statistics.mean(values), 1)
            record[metric + '_std'] = round(sample_std(values), 1)
        summary.append(record)
    with (args.output / 'summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f'Generated three PDFs and summary.csv in {args.output}')


if __name__ == '__main__':
    main()
