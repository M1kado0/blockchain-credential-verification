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
