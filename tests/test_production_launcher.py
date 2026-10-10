"""Exercise shell dispatch without launching simulations or changing real runs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/run_full_production.sh'


@pytest.fixture
def launcher(tmp_path):
    shim = tmp_path / 'python shim'
    shim.write_text(f'''#!{sys.executable}
import json, os, subprocess, sys
if sys.argv[1] == '-':
    raise SystemExit(subprocess.run([sys.executable, *sys.argv[1:]], input=sys.stdin.read(), text=True).returncode)
assert os.environ['ASTRA_BIN'] == os.environ['PRODUCTION_TEST_EXPECT_ASTRA']
with open(os.environ['PRODUCTION_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
if 'run-constrained' in sys.argv and os.environ.get('PRODUCTION_TEST_FAIL'):
    raise SystemExit(7)
''')
    shim.chmod(0o755)
    binary = tmp_path / 'custom astra'
    binary.write_text('#!/bin/sh\nexit 0\n')
    binary.chmod(0o755)
    log = tmp_path / 'commands.jsonl'
    env = dict(os.environ, PYTHON_BIN=str(shim), ASTRA_BIN=str(binary), GENERATOR_BIN=str(binary),
               PRODUCTION_TEST_LOG=str(log), PRODUCTION_TEST_EXPECT_ASTRA=str(binary))
    def run(*args):
        result = subprocess.run(['bash', str(SCRIPT), *map(str, args)], cwd=ROOT, env=env,
                                text=True, capture_output=True)
        commands = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, commands
    return run, env


def test_pipeline_dispatches_shared_config_reference_and_audit_workers(launcher, tmp_path):
    run, env = launcher
    root = tmp_path / 'campaign; with spaces'
    result, commands = run('--output-dir', root, '--p1-case', 'balanced', '--quiet', '--workers', 2)
    assert result.returncode == 0, result.stderr
    assert len(commands) == 5
    for command in commands[:3]:
        assert command[command.index('--config') + 1] == 'configs/publication_200MeV.yaml'
        i = command.index('--reporting-ref-point')
        assert command[i + 1:i + 4] == ['-0.0000015', '-0.0000015', '-1500000']
        assert command[command.index('--num-workers') + 1] == '2'
        assert command[command.index('--output-dir') + 1].startswith(str(root))
    assert commands[-1][commands[-1].index('--input') + 1].endswith('/pareto_feasible.csv')
    assert '--num-workers' in commands[-2]
    assert len(list((root / 'logs').glob('*.log'))) == 5
    assert env['ASTRA_BIN'].endswith('custom astra')


def test_pipeline_stops_before_analysis_when_campaign_fails(launcher, tmp_path):
    run, env = launcher
    env['PRODUCTION_TEST_FAIL'] = '1'
    result, commands = run('--output-dir', tmp_path / 'failed', '--quiet')
    assert result.returncode != 0
    assert len(commands) == 3
    assert 'phase3 failed' in result.stderr


def test_pipeline_preview_creates_no_output(launcher, tmp_path):
    run, _ = launcher
    root = tmp_path / 'preview'
    result, commands = run('--output-dir', root, '--dry-run')
    assert result.returncode == 0, result.stderr
    assert not root.exists() and not commands
    assert 'run-scalarized' in result.stdout and 'pareto_feasible.csv' in result.stdout


@pytest.mark.parametrize('args', [['--workers', '0'], ['--iterations'], ['--p1-case', 'invalid']])
def test_pipeline_invalid_arguments_do_not_create_output(launcher, tmp_path, args):
    run, _ = launcher
    root = tmp_path / 'invalid'
    result, commands = run('--output-dir', root, *args)
    assert result.returncode != 0 and not root.exists() and not commands


def test_pipeline_resume_uses_saved_config_and_dedicated_command(launcher, tmp_path):
    run, _ = launcher
    root = tmp_path / 'resume'
    for relative in ['phase1_scalarized/balanced', 'phase2_unconstrained', 'phase3_constrained']:
        path = root / relative / 'checkpoints'
        path.mkdir(parents=True)
        (path / 'checkpoint.pt').write_bytes(b'fake checkpoint for command dispatch only')
    saved = root / 'phase3_constrained/config.yaml'
    saved.write_bytes((ROOT / 'configs/publication_200MeV.yaml').read_bytes())
    result, commands = run('--output-dir', root, '--resume', '--p1-case', 'balanced', '--quiet')
    assert result.returncode == 0, result.stderr
    resumes = [command for command in commands if 'resume' in command]
    assert len(resumes) == 3
    for command in resumes:
        assert '--run-dir' in command and '--n-iterations' in command
        assert '--config' not in command and '--seed' not in command and '--batch-size' not in command
    assert str(saved) in commands[-1] and str(saved) in commands[-2]


def test_pipeline_uses_configured_cases_and_records_launch_inputs(launcher, tmp_path):
    run, _ = launcher
    root = tmp_path / 'record'
    result, commands = run('--output-dir', root, '--quiet', '--mock-evaluator')
    assert result.returncode == 0, result.stderr
    suite = commands[0]
    assert suite[suite.index('run-scalarized-suite') + 1] == '--cases'
    configured = ['balanced', 'high_brightness', 'low_energy_spread', 'x_dominant', 'y_dominant']
    assert suite[suite.index('--cases') + 1:suite.index('--cases') + 6] == configured
    assert all('--mock-evaluator' in command for command in commands)  # every step rehearses without ASTRA
    assert [command[2] for command in commands] == [
        'run-scalarized-suite', 'run-unconstrained', 'run-constrained', 'compare', 'run-robustness']
    record = json.loads(next((root / 'logs').glob('launch_*.json')).read_text())
    assert record['mock_evaluator'] and record['config']['sha256']
    assert record['reporting_ref_point_model'] == [-1.5e-6, -1.5e-6, -1.5e6]


def test_pipeline_rejects_unresolvable_executable_before_creating_output(launcher, tmp_path):
    run, env = launcher
    config = tmp_path / 'missing_executable.yaml'
    text = (ROOT / 'configs/publication_200MeV.yaml').read_text()
    config.write_text(text.replace('executable: "../bin/astra"', f'executable: "{tmp_path}/absent"')
                      .replace('template_dir: ".."', f'template_dir: "{ROOT}"'))
    env['ASTRA_BIN'] = str(tmp_path / 'also absent')
    env['PATH'] = '/usr/bin:/bin'
    root = tmp_path / 'no_executable'
    result, commands = run('--output-dir', root, '--config', config)
    assert result.returncode != 0 and not root.exists() and not commands
    assert 'ASTRA executable' in result.stderr
