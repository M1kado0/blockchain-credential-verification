import csv
import pytest
from src import generate_figures

FIELDS = ['method', 'batch_size', 'repeat', 'revocation_fraction', 'revoked_count',
          'issue_gas_per_credential', 'revoke_total_gas', 'revoke_mean_gas',
          'verify_estimate_gas', 'verify_call_median_ms', 'proof_bytes']

# method, n, r, k, repeat, issuance gas per credential, total revocation gas,
# verification estimate, proof bytes
FIXTURE = [
    ('individual', 3, 0.5, 1, 0, 73310.0, 47600, 36713, 0),
    ('individual', 8, 0.0, 0, 0, 73308.0, 0, 36709, 0),
    ('individual', 8, 0.0, 0, 1, 73310.0, 0, 36709, 0),
    ('individual', 8, 0.01, 0, 0, 73312.0, 0, 36709, 0),
    ('individual', 8, 0.5, 4, 0, 73308.0, 190400, 36709, 0),
    ('individual', 8, 0.5, 4, 1, 73308.0, 190408, 36709, 0),
    ('merkle_batch', 3, 0.5, 1, 0, 24434.0, 48813, 38600, 64),
    ('merkle_batch', 8, 0.0, 0, 0, 9162.0, 0, 39040, 96),
    ('merkle_batch', 8, 0.0, 0, 1, 9163.0, 0, 39040, 96),
    ('merkle_batch', 8, 0.01, 0, 0, 9164.0, 0, 39040, 96),
    ('merkle_batch', 8, 0.5, 4, 0, 9162.0, 195220, 39040, 96),
    ('merkle_batch', 8, 0.5, 4, 1, 9162.0, 195260, 39040, 96),
]


@pytest.fixture(scope='module')
def summary(tmp_path_factory):
    root = tmp_path_factory.mktemp('figures')
    source = root / 'benchmark.csv'
    with source.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for method, n, r, k, repeat, issue, revoke, verify, proof in FIXTURE:
            writer.writerow([method, n, repeat, r, k, issue, revoke, revoke / k if k else 0,
                             verify, 1.5, proof])
    out = root / 'out'
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr('sys.argv', ['generate_figures', '--input', str(source), '--output', str(out)])
        generate_figures.main()
    for pdf in ('issuance_scaling.pdf', 'verification_gas.pdf', 'local_call_latency.pdf'):
        assert (out / pdf).exists(), pdf
    with (out / 'summary.csv').open() as f:
        return {(r['method'], r['batch_size'], r['revoked_count']): r for r in csv.DictReader(f)}


def test_summary_has_one_entry_per_method_size_and_actual_k(summary):
    assert sorted(summary) == [
        ('individual', '3', '1'), ('individual', '8', '0'), ('individual', '8', '4'),
        ('merkle_batch', '3', '1'), ('merkle_batch', '8', '0'), ('merkle_batch', '8', '4')]


def test_mean_and_sample_std_come_from_measured_rows(summary):
    # Sample std (n - 1 denominator): 73308, 73310, 73312 -> 2.0; population std would be 1.6.
    ind = summary[('individual', '8', '0')]
    assert ind['issue_gas_per_credential_mean'] == '73310.0'
    assert ind['issue_gas_per_credential_std'] == '2.0'
    revoked = summary[('individual', '8', '4')]
    assert revoked['revoke_total_gas_mean'] == '190404.0'
    assert revoked['revoke_total_gas_std'] == '5.7'
    assert revoked['revoke_mean_gas_mean'] == '47601.0'
    assert revoked['revoke_mean_gas_std'] == '1.4'
    batch = summary[('merkle_batch', '8', '4')]
    assert batch['revoke_total_gas_mean'] == '195240.0'
    assert batch['revoke_total_gas_std'] == '28.3'
    assert batch['verify_estimate_gas_mean'] == '39040.0'
    assert batch['proof_bytes_mean'] == '96.0'
    assert summary[('merkle_batch', '8', '0')]['issue_gas_per_credential_std'] == '1.0'


def test_single_repeat_has_zero_std(summary):
    single = summary[('merkle_batch', '3', '1')]
    assert single['repeats'] == '1'
    assert single['issue_gas_per_credential_mean'] == '24434.0'
    for metric in generate_figures.TABLE_METRICS:
        assert single[metric + '_std'] == '0.0'


def test_entry_states_repeats_and_pooled_fractions(summary):
    # r = 0 and r = 0.01 both give k = 0 at n = 8, so they share one entry.
    pooled = summary[('individual', '8', '0')]
    assert pooled['repeats'] == '3'
    assert pooled['revocation_fractions'] == '0.0;0.01'
    assert summary[('individual', '8', '4')]['revocation_fractions'] == '0.5'


def test_per_revocation_gas_is_blank_when_nothing_was_revoked(summary):
    # Mean gas per revocation is undefined at k = 0; total revocation gas is a measured 0.
    none_revoked = summary[('merkle_batch', '8', '0')]
    assert none_revoked['revoke_mean_gas_mean'] == '' and none_revoked['revoke_mean_gas_std'] == ''
    assert none_revoked['revoke_total_gas_mean'] == '0.0'
