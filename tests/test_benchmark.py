import csv
import math
import pytest
from src import benchmark


def read_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp('bench') / 'benchmark.csv'
    benchmark.run([3, 7, 8], [0.0, 0.01, 0.5], 1, 2, 42, out)
    return read_rows(out)


def test_actual_k_is_floor_of_fraction_times_size(rows):
    assert len(rows) == 3 * 3 * 2
    for r in rows:
        assert int(r['revoked_count']) == math.floor(float(r['revocation_fraction']) * int(r['batch_size']))
    zero = [r for r in rows if r['batch_size'] == '8' and r['revocation_fraction'] == '0.01']
    assert {r['revoked_count'] for r in zero} == {'0'}
    assert {r['revoked_count'] for r in rows if r['batch_size'] == '7' and r['revocation_fraction'] == '0.5'} == {'3'}


def test_both_methods_report_same_k(rows):
    by_config = {}
    for r in rows:
        by_config.setdefault((r['batch_size'], r['revocation_fraction']), set()).add(
            (r['method'], r['revoked_count']))
    for pairs in by_config.values():
        assert len(pairs) == 2 and len({k for _, k in pairs}) == 1


def test_revocation_gas_fields(rows):
    for r in rows:
        k, total = int(r['revoked_count']), int(r['revoke_total_gas'])
        assert 'revoke_gas' not in r
        if k == 0:
            assert total == 0 and float(r['revoke_mean_gas']) == 0
        else:
            assert total > 0 and float(r['revoke_mean_gas']) == total / k
        assert int(r['revoked_rejected']) == k


def test_write_gas_per_credential_recomputed_from_raw_columns(rows):
    for r in rows:
        expected = (int(r['issue_total_gas']) + int(r['revoke_total_gas'])) / int(r['batch_size'])
        assert float(r['write_gas_per_credential']) == expected


def test_setup_gas_is_recorded_separately_per_method(rows):
    for r in rows:
        assert int(r['deploy_gas']) > 0 and int(r['authorize_gas']) > 0
    for method in ('individual', 'merkle_batch'):
        assert len({(r['deploy_gas'], r['authorize_gas']) for r in rows if r['method'] == method}) == 1


def test_wrong_outcome_aborts_before_csv(tmp_path, monkeypatch):
    real = benchmark.transact

    def skip_revokes(w3, fn, account):
        if fn.fn_name in ('revoke', 'revokeCredential'):
            return type('R', (), {'gasUsed': 0})()
        return real(w3, fn, account)

    monkeypatch.setattr(benchmark, 'transact', skip_revokes)
    out = tmp_path / 'benchmark.csv'
    with pytest.raises(RuntimeError):
        benchmark.run([3], [0.5], 1, 1, 42, out)
    assert not out.exists()


@pytest.mark.parametrize('argv', [
    ['--fractions', '1.5'], ['--fractions', '-0.1'], ['--sizes', '0'],
    ['--repeats', '0'], ['--queries', '0']])
def test_invalid_arguments_rejected(argv, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('sys.argv', ['benchmark', '--output', str(tmp_path / 'x.csv')] + argv)
    with pytest.raises(SystemExit) as e:
        benchmark.main()
    assert e.value.code == 2
    assert not (tmp_path / 'x.csv').exists()


def test_run_rejects_invalid_arguments_directly(tmp_path):
    for args in ([[0], [0.1], 1, 1], [[3], [2.0], 1, 1], [[3], [0.1], 0, 1]):
        with pytest.raises(ValueError):
            benchmark.run(*args, 42, tmp_path / 'x.csv')


GAS_COLUMNS = ['issue_total_gas', 'issue_gas_per_credential', 'issue_calldata_bytes',
               'verify_estimate_gas', 'revoke_total_gas', 'write_gas_per_credential',
               'deploy_gas', 'authorize_gas']


def test_defaults_equal_proposal_workload(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(benchmark, 'run', lambda *a: captured.update(args=a))
    monkeypatch.setattr('sys.argv', ['benchmark', '--output', str(tmp_path / 'x.csv')])
    benchmark.main()
    sizes, fractions, repeats, queries, seed, _ = captured['args']
    assert sizes == [1, 3, 7, 8, 31, 32, 127, 128, 512]
    assert fractions == [0.0, 0.01, 0.10, 0.50]
    assert repeats == 5 and seed == 42


def test_cli_overrides_give_expected_row_count(tmp_path, monkeypatch):
    out = tmp_path / 'b.csv'
    monkeypatch.setattr('sys.argv', ['benchmark', '--output', str(out), '--sizes', '1', '3',
                                     '--fractions', '0', '0.5', '--repeats', '2', '--queries', '1'])
    benchmark.main()
    assert len(read_rows(out)) == 2 * 2 * 2 * 2


def test_same_seed_gives_identical_gas_columns(tmp_path):
    outs = []
    for name in ('a', 'b'):
        out = tmp_path / f'{name}.csv'
        benchmark.run([3], [0.5], 2, 1, 42, out)
        outs.append([[r[c] for c in GAS_COLUMNS] for r in read_rows(out)])
    assert outs[0] == outs[1]


def test_progress_printed_per_configuration(tmp_path, capsys):
    benchmark.run([1, 3], [0.0, 0.5], 1, 1, 42, tmp_path / 'p.csv')
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith('completed')]
    assert len(lines) == 4
    assert '1/4' in lines[0] and '4/4' in lines[-1]


def test_metadata_has_every_required_field(tmp_path):
    import hashlib
    import json
    import subprocess
    out = tmp_path / 'm.csv'
    benchmark.run([1], [0.0], 1, 1, 42, out)
    meta = json.loads(out.with_suffix('.metadata.json').read_text())
    for key in ['seed', 'sizes', 'fractions', 'repeats', 'queries', 'compiler_settings',
                'packages', 'platform', 'source_sha256', 'git_revision', 'csv_sha256']:
        assert key in meta, key
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=benchmark.ROOT, text=True).strip()
    assert meta['git_revision'] == head
    assert meta['csv_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
