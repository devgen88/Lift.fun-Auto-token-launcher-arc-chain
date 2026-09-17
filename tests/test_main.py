from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock

import pytest
from web3 import Web3

import main


PRIVATE_KEY = "0x" + "11" * 32


def test_parse_e6() -> None:
    assert main.parse_e6("0") == 0
    assert main.parse_e6("1.25") == 1_250_000
    with pytest.raises(ValueError):
        main.parse_e6("0.0000001")


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image = tmp_path / "token.png"
    image.write_bytes(b"png")
    monkeypatch.setenv("PRIVATE_KEY", PRIVATE_KEY)
    monkeypatch.setenv("TOKEN_IMAGE", str(image))
    for name in ("TOKEN_NAME", "TOKEN_SYMBOL", "INITIAL_BUY", "CREATOR_ADDRESS"):
        monkeypatch.delenv(name, raising=False)

    config = main.load_config(Namespace(image=None, name=None, symbol=None, dry_run=False))

    assert config.name == "DXM"
    assert config.symbol == "DXM"
    assert config.chain_id == 5042
    assert config.initial_buy_e6 == 0


def test_upload_and_metadata_requests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image = tmp_path / "token.jpg"
    image.write_bytes(b"image-data")
    monkeypatch.setenv("PRIVATE_KEY", PRIVATE_KEY)
    monkeypatch.setenv("TOKEN_IMAGE", str(image))
    config = main.load_config(Namespace(image=None, name=None, symbol=None, dry_run=True))
    responses = [
        Mock(status_code=200, json=lambda: {"url": "https://api.lift.fun/image/1"}),
        Mock(status_code=200, json=lambda: {"uri": "https://api.lift.fun/metadata/1"}),
    ]
    for response in responses:
        response.raise_for_status.return_value = None
    request = Mock(side_effect=responses)
    monkeypatch.setattr(main.requests, "request", request)

    image_url = main.upload_image(config)
    metadata_uri = main.create_metadata(config, image_url)

    assert metadata_uri.endswith("/metadata/1")
    assert request.call_args_list[0].kwargs["files"]["image"][0] == "token.jpg"
    assert request.call_args_list[1].kwargs["json"]["image_url"] == image_url


def test_launch_abi_has_captured_selector() -> None:
    contract = Web3().eth.contract(
        address="0x1ca37B3C40e89aaD48b5ad3352269c2293CFD3DA",
        abi=main.FACTORY_ABI,
    )
    params = (
        "DXM",
        "DXM",
        bytes(32),
        "0x1111111111111111111111111111111111111111",
        "https://api.lift.fun/api/v1/metadata/test",
        0,
        0,
        "0x44b453d355835ce1269fc11d3fa4161c0dcc0087",
        0,
        0,
        (10_000, 0, 0, 0),
        0,
        0,
        False,
        [],
        bytes(32),
    )

    assert contract.encode_abi("launch", args=[params]).startswith("0x02efedf5")
