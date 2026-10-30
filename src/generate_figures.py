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
# (method key, legend name, color, line style). Fractions are told apart by marker.
METHODS = [('individual', 'Individual registry', '#2a78d6', '-'),
           ('merkle_batch', 'Merkle batch', '#eb6834', '--')]
FRACTION_MARKERS = ['o', 's', '^', 'D']


def sample_std(values):
    """Sample standard deviation (n - 1 denominator); zero for a single value."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def write_gas_figure(rows):
    """Figure 1: C_write per credential against batch size, one line per method and fraction."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row['method'], float(row['revocation_fraction']), int(row['batch_size']))].append(
            float(row['write_gas_per_credential']))
    fractions = sorted({fraction for _, fraction, _ in groups})
    if len(fractions) > len(FRACTION_MARKERS):
        raise ValueError(f'Figure 1 has markers for {len(FRACTION_MARKERS)} fractions, got {fractions}')
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for method, name, color, style in METHODS:
        for fraction, marker in zip(fractions, FRACTION_MARKERS):
            sizes = sorted(n for m, r, n in groups if (m, r) == (method, fraction))
            if not sizes:
                continue
            values = [groups[(method, fraction, n)] for n in sizes]
            ax.errorbar(sizes, [statistics.mean(v) for v in values],
                        yerr=[sample_std(v) for v in values], color=color, linestyle=style,
                        # Hollow, so r = 0 still shows under r = 0.01 wherever both give k = 0.
                        marker=marker, fillstyle='none', capsize=3,
                        label=f'{name}, r = {fraction:g}')
    ax.set_xscale('log', base=2)
    ax.set_yscale('log')
    # Ticks at the measured sizes, printed as plain counts instead of powers of two.
    sizes = sorted({n for _, _, n in groups})
    ax.set_xticks(sizes, [str(n) for n in sizes])
    ax.set_xticks([], minor=True)
    ax.set_xlabel('Batch size (credential count)')
    ax.set_ylabel('Write gas per credential (gas units)')
    ax.grid(alpha=.25)
    ax.legend(fontsize=8, ncol=2, loc='upper center', bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    return fig


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
    fig = write_gas_figure(rows)
    fig.savefig(args.output / 'write_gas.pdf')
    plt.close(fig)
    for metric, label, filename in [
        ('verify_estimate_gas', 'Simulated verification transaction estimate (gas units)', 'verification_gas.pdf'),
        ('verify_call_median_ms', 'Local EVM eth_call duration (ms)', 'local_call_latency.pdf')]:
        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        for method, name, color, _ in METHODS:
            sizes = sorted(n for m, n in plot_groups if m == method)
            values = [[float(r[metric]) for r in plot_groups[(method, n)]] for n in sizes]
            ax.errorbar(sizes, [statistics.mean(v) for v in values],
                        yerr=[sample_std(v) for v in values],
                        color=color, marker='o', capsize=3, label=name)
        ax.set_xscale('log', base=2)
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
