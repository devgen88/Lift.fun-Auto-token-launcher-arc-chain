from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3


FACTORY_ABI = [
    {
        "type": "function",
        "name": "launchFeeWei",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "launchTermsHash",
        "stateMutability": "view",
        "inputs": [{"name": "quote", "type": "address"}],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "type": "function",
        "name": "predictToken",
        "stateMutability": "view",
        "inputs": [
            {"name": "salt", "type": "bytes32"},
            {"name": "name", "type": "string"},
            {"name": "symbol", "type": "string"},
        ],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "type": "function",
        "name": "launch",
        "stateMutability": "payable",
        "inputs": [
            {
                "name": "p",
                "type": "tuple",
                "components": [
                    {"name": "name", "type": "string"},
                    {"name": "symbol", "type": "string"},
                    {"name": "salt", "type": "bytes32"},
                    {"name": "creator", "type": "address"},
                    {"name": "metadataURI", "type": "string"},
                    {"name": "initialBuyE6", "type": "uint256"},
                    {"name": "minTokensOut", "type": "uint256"},
                    {"name": "quote", "type": "address"},
                    {"name": "creatorTaxBuyBps", "type": "uint16"},
                    {"name": "creatorTaxSellBps", "type": "uint16"},
                    {
                        "name": "split",
                        "type": "tuple",
                        "components": [
                            {"name": "creatorBps", "type": "uint16"},
                            {"name": "burnBps", "type": "uint16"},
                            {"name": "dividendBps", "type": "uint16"},
                            {"name": "liquidityBps", "type": "uint16"},
                        ],
                    },
                    {"name": "minHolderBalance", "type": "uint256"},
                    {"name": "creatorBaseTo", "type": "uint8"},
                    {"name": "guarded", "type": "bool"},
                    {"name": "snipeExempt", "type": "address[]"},
                    {"name": "expectedTermsHash", "type": "bytes32"},
                ],
            }
        ],
        "outputs": [
            {"name": "token", "type": "address"},
            {"name": "poolId", "type": "bytes32"},
            {"name": "positionId", "type": "uint256"},
        ],
    },
]

ERC20_ABI = [
    {
        "type": "function",
        "name": "allowance",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value.strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if value.strip().lower() in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def parse_e6(value: str) -> int:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid INITIAL_BUY value: {value}") from exc
    if amount < 0 or amount.as_tuple().exponent < -6:
        raise ValueError("INITIAL_BUY must be non-negative with at most 6 decimals")
    return int(amount * 1_000_000)


def checked_address(value: str, name: str) -> str:
    if not Web3.is_address(value):
        raise ValueError(f"{name} is not a valid address: {value}")
    return Web3.to_checksum_address(value)


@dataclass(frozen=True)
class Config:
    private_key: str
    image: Path
    name: str
    symbol: str
    description: str
    website: str
    x: str
    telegram: str
    api_url: str
    rpc_url: str
    chain_id: int
    factory: str
    quote: str
    creator: str | None
    initial_buy_e6: int
    min_tokens_out: int
    tax_buy_bps: int
    tax_sell_bps: int
    min_holder_balance: int
    creator_base_to: int
    guarded: bool
    dry_run: bool
    timeout: int


def load_config(args: argparse.Namespace) -> Config:
    private_key = os.getenv("PRIVATE_KEY", "").strip()
    image_value = args.image or os.getenv("TOKEN_IMAGE", "")
    if not private_key:
        raise ValueError("PRIVATE_KEY is required in .env")
    try:
        Account.from_key(private_key)
    except Exception as exc:
        raise ValueError("PRIVATE_KEY is not a valid 32-byte private key") from exc
    if not image_value:
        raise ValueError("Set TOKEN_IMAGE in .env or pass --image")

    name = (args.name or os.getenv("TOKEN_NAME", "DXM")).strip()
    symbol = (args.symbol or os.getenv("TOKEN_SYMBOL", "DXM")).strip().upper()
    if not name or not symbol:
        raise ValueError("TOKEN_NAME and TOKEN_SYMBOL cannot be empty")

    config = Config(
        private_key=private_key,
        image=Path(image_value).expanduser().resolve(),
        name=name,
        symbol=symbol,
        description=os.getenv("TOKEN_DESCRIPTION", "").strip(),
        website=os.getenv("TOKEN_WEBSITE", "").strip(),
        x=os.getenv("TOKEN_X", "").strip(),
        telegram=os.getenv("TOKEN_TELEGRAM", "").strip(),
        api_url=os.getenv("LIFT_API_URL", "https://api.lift.fun/api/v1").rstrip("/"),
        rpc_url=os.getenv("ARC_RPC_URL", "https://rpc.blockdaemon.mainnet.arc.io"),
        chain_id=int(os.getenv("ARC_CHAIN_ID", "5042")),
        factory=checked_address(
            os.getenv("LIFT_FACTORY", "0x1ca37B3C40e89aaD48b5ad3352269c2293CFD3DA"),
            "LIFT_FACTORY",
        ),
        quote=checked_address(
            os.getenv("QUOTE_TOKEN", "0x44b453d355835ce1269fc11d3fa4161c0dcc0087"),
            "QUOTE_TOKEN",
        ),
        creator=os.getenv("CREATOR_ADDRESS", "").strip() or None,
        initial_buy_e6=parse_e6(os.getenv("INITIAL_BUY", "0")),
        min_tokens_out=int(os.getenv("MIN_TOKENS_OUT", "0")),
        tax_buy_bps=int(os.getenv("CREATOR_TAX_BUY_BPS", "0")),
        tax_sell_bps=int(os.getenv("CREATOR_TAX_SELL_BPS", "0")),
        min_holder_balance=int(os.getenv("MIN_HOLDER_BALANCE", "0")),
        creator_base_to=int(os.getenv("CREATOR_BASE_TO", "0")),
        guarded=env_bool("GUARDED", False),
        dry_run=args.dry_run or env_bool("DRY_RUN", False),
        timeout=int(os.getenv("TX_TIMEOUT", "180")),
    )
    if not config.image.is_file():
        raise ValueError(f"Image file not found: {config.image}")
    if config.creator:
        checked_address(config.creator, "CREATOR_ADDRESS")
    for field, value in (
        ("CREATOR_TAX_BUY_BPS", config.tax_buy_bps),
        ("CREATOR_TAX_SELL_BPS", config.tax_sell_bps),
    ):
        if not 0 <= value <= 10_000:
            raise ValueError(f"{field} must be between 0 and 10000")
    if config.min_tokens_out < 0 or config.min_holder_balance < 0:
        raise ValueError("MIN_TOKENS_OUT and MIN_HOLDER_BALANCE cannot be negative")
    if not 0 <= config.creator_base_to <= 255:
        raise ValueError("CREATOR_BASE_TO must be between 0 and 255")
    return config


def api_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = requests.request(method, url, timeout=60, **kwargs)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        detail = getattr(getattr(exc, "response", None), "text", "")
        raise RuntimeError(f"Lift API request failed: {exc} {detail}".strip()) from exc
    if not isinstance(result, dict):
        raise RuntimeError("Lift API returned an unexpected response")
    return result


def upload_image(config: Config) -> str:
    mime = mimetypes.guess_type(config.image.name)[0] or "application/octet-stream"
    with config.image.open("rb") as image_file:
        result = api_request(
            "POST",
            f"{config.api_url}/images",
            headers={"Accept": "application/json", "Origin": "https://lift.fun"},
            files={"image": (config.image.name, image_file, mime)},
        )
    if not result.get("url"):
        raise RuntimeError(f"Image upload response has no URL: {result}")
    return str(result["url"])


def create_metadata(config: Config, image_url: str) -> str:
    payload = {
        "name": config.name,
        "symbol": config.symbol,
        "description": config.description,
        "image_url": image_url,
        "website": config.website,
        "x": config.x,
        "telegram": config.telegram,
    }
    result = api_request(
        "POST",
        f"{config.api_url}/metadata",
        headers={"Accept": "application/json", "Origin": "https://lift.fun"},
        json=payload,
    )
    if not result.get("uri"):
        raise RuntimeError(f"Metadata response has no URI: {result}")
    return str(result["uri"])


def fee_fields(web3: Web3) -> dict[str, int]:
    block = web3.eth.get_block("pending")
    base_fee = int(block.get("baseFeePerGas", 0))
    priority = int(os.getenv("MAX_PRIORITY_FEE_WEI", "0"))
    configured = os.getenv("MAX_FEE_PER_GAS_WEI")
    max_fee = int(configured) if configured else max(base_fee * 2 + priority, web3.eth.gas_price)
    return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": priority}


def send_contract_transaction(
    web3: Web3,
    account: Any,
    function: Any,
    chain_id: int,
    timeout: int,
    value: int = 0,
) -> str:
    tx_base = {
        "from": account.address,
        "chainId": chain_id,
        "nonce": web3.eth.get_transaction_count(account.address, "pending"),
        "value": value,
        **fee_fields(web3),
    }
    estimate = function.estimate_gas({"from": account.address, "value": value})
    transaction = function.build_transaction({**tx_base, "gas": estimate * 120 // 100})
    signed = account.sign_transaction(transaction)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return tx_hash.hex()


def launch(config: Config, metadata_uri: str) -> dict[str, Any]:
    web3 = Web3(Web3.HTTPProvider(config.rpc_url, request_kwargs={"timeout": 30}))
    if not web3.is_connected():
        raise RuntimeError(f"Cannot connect to Arc RPC: {config.rpc_url}")
    actual_chain_id = web3.eth.chain_id
    if actual_chain_id != config.chain_id:
        raise RuntimeError(f"RPC chain ID is {actual_chain_id}, expected {config.chain_id}")

    account = Account.from_key(config.private_key)
    creator = checked_address(config.creator, "CREATOR_ADDRESS") if config.creator else account.address
    factory = web3.eth.contract(address=config.factory, abi=FACTORY_ABI)
    salt = secrets.token_bytes(32)
    launch_fee = factory.functions.launchFeeWei().call()
    terms_hash = factory.functions.launchTermsHash(config.quote).call()
    predicted_token = factory.functions.predictToken(salt, config.name, config.symbol).call()
    params = (
        config.name,
        config.symbol,
        salt,
        creator,
        metadata_uri,
        config.initial_buy_e6,
        config.min_tokens_out,
        config.quote,
        config.tax_buy_bps,
        config.tax_sell_bps,
        (10_000, 0, 0, 0),
        config.min_holder_balance,
        config.creator_base_to,
        config.guarded,
        [],
        terms_hash,
    )

    summary = {
        "wallet": account.address,
        "creator": creator,
        "metadata_uri": metadata_uri,
        "predicted_token": predicted_token,
        "launch_fee_wei": launch_fee,
        "initial_buy_e6": config.initial_buy_e6,
        "salt": Web3.to_hex(salt),
    }
    print(json.dumps(summary, indent=2))
    if config.dry_run:
        print("Dry run: metadata was created, but no blockchain transactions were sent.")
        return summary

    approval_hash = None
    if config.initial_buy_e6:
        quote = web3.eth.contract(address=config.quote, abi=ERC20_ABI)
        allowance = quote.functions.allowance(account.address, config.factory).call()
        if allowance < config.initial_buy_e6:
            approval_hash = send_contract_transaction(
                web3,
                account,
                quote.functions.approve(config.factory, config.initial_buy_e6),
                config.chain_id,
                config.timeout,
            )
            print(f"Approval confirmed: {approval_hash}")

    tx_hash = send_contract_transaction(
        web3,
        account,
        factory.functions.launch(params),
        config.chain_id,
        config.timeout,
        value=launch_fee,
    )
    summary.update({"approval_tx": approval_hash, "launch_tx": tx_hash})
    print(f"Launch confirmed: {tx_hash}")
    print(f"Token address: {predicted_token}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload metadata and launch a token on Lift.fun")
    parser.add_argument("--image", help="Token image path; overrides TOKEN_IMAGE")
    parser.add_argument("--name", help="Token name; overrides TOKEN_NAME")
    parser.add_argument("--symbol", help="Token symbol; overrides TOKEN_SYMBOL")
    parser.add_argument("--dry-run", action="store_true", help="Upload only; do not send transactions")
    return parser


def main() -> int:
    load_dotenv()
    try:
        config = load_config(build_parser().parse_args())
        print(f"Uploading image: {config.image}")
        image_url = upload_image(config)
        print(f"Image uploaded: {image_url}")
        metadata_uri = create_metadata(config, image_url)
        print(f"Metadata created: {metadata_uri}")
        launch(config, metadata_uri)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
