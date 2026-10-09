"""Device policy validation without requiring a physical CUDA allocation."""

import pytest
import torch
from mobo_linac.utils import get_device


@pytest.mark.parametrize("device_request", ["cuda", "cuda:0", torch.device("cuda"), torch.device("cuda:0")])
def test_unavailable_cuda_requests_use_consistent_fallback(monkeypatch, device_request):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert get_device(device_request) == torch.device("cpu")
    with pytest.raises(ValueError, match="unavailable"):
        get_device(device_request, allow_cpu_fallback=False)


@pytest.mark.parametrize("device_request", [None, "auto", "", "cpu", torch.device("cpu")])
def test_cpu_and_auto_without_cuda(monkeypatch, device_request):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert get_device(device_request) == torch.device("cpu")


def test_cuda_policy_checks_indices_with_available_hardware(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 0)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 2)
    for device_request in (None, "auto", "cuda", "cuda:0", torch.device("cuda:0")):
        assert get_device(device_request) == torch.device("cuda:0")
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 1)
    assert get_device("cuda") == torch.device("cuda:1")
    assert get_device("auto") == torch.device("cuda:1")
    assert get_device("cuda:1") == torch.device("cuda:1")
    with pytest.raises(ValueError, match="index"):
        get_device("cuda:2")


def test_invalid_devices_fail_before_campaign_output(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    for request in ("garbage", "mps"):
        output = tmp_path / request
        with pytest.raises(ValueError):
            MoboCampaignRunner(output_dir=output, device=request)
        assert not output.exists()


@pytest.mark.parametrize("device_request", ["cuda", "cuda:0", torch.device("cuda:0")])
def test_campaign_uses_shared_unavailable_cuda_policy(tmp_path, monkeypatch, device_request):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    runner = MoboCampaignRunner(output_dir=tmp_path, device=device_request)
    assert runner.device == torch.device("cpu")
