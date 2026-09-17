# Lift.fun Auto Token Launcher

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Network](https://img.shields.io/badge/Arc-Chain%205042-6C5CE7)](https://lift.fun/)
[![Factory](https://img.shields.io/badge/Lift-V4%20Factory-00C2A8)](https://lift.fun/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-not%20specified-lightgrey)](#license)

> Upload token artwork, publish Lift metadata, and launch a token through Lift's V4 factory on Arc without relying on stale captured calldata.

## Repository Details

| Field | Value |
| --- | --- |
| **Repository name** | `Lift-fun-auto-token-launcher` |
| **Description** | Python CLI for uploading token metadata and launching tokens through Lift's V4 factory on Arc |
| **Project URL** | [https://lift.fun](https://lift.fun/) |
| **Runtime config** | [https://lift.fun/config.js](https://lift.fun/config.js) |
| **Network** | Arc, chain ID `5042` |
| **Topics / tags** | `lift-fun`, `arc`, `token-launcher`, `web3`, `python`, `erc20`, `defi`, `cli` |

```text
Lift-fun-auto-token-launcher/
|-- .env.example
|-- .gitignore
|-- README.md
|-- main.py
|-- requirements-dev.txt
|-- requirements.txt
|-- run.bat
`-- tests/
    `-- test_main.py
```


## Overview

The launcher performs the complete token-launch workflow from one command:

1. Reads and validates token, wallet, network, and launch settings.
2. Uploads the token image to the Lift API.
3. Creates public token metadata from the configured name, symbol, description, and social links.
4. Connects to the configured Arc RPC and verifies its chain ID.
5. Reads the **current launch fee** and **terms hash** from the V4 factory.
6. Predicts the token address with a fresh random salt.
7. Approves the quote token when an initial buy requires additional allowance.
8. Signs and submits the launch transaction, then waits for confirmation.

The launch split is currently fixed at `100%` creator and the snipe-exempt address list is empty.

## Key Features

- **Live on-chain parameters:** Reads `launchFeeWei()` and `launchTermsHash()` immediately before launch.
- **Automatic metadata publishing:** Uploads artwork and metadata through Lift's API.
- **Deterministic address preview:** Calls `predictToken()` before submitting the transaction.
- **Optional initial buy:** Converts human-readable amounts to the quote token's 6-decimal units.
- **Allowance management:** Sends an ERC-20 approval only when the existing allowance is insufficient.
- **EIP-1559 transactions:** Supports configurable priority and maximum gas fees.
- **Safety checks:** Validates private keys, addresses, image paths, chain ID, tax limits, and numeric ranges.
- **Dry-run mode:** Publishes the image and metadata without sending approval or launch transactions.
- **CLI overrides:** Overrides image, name, and symbol without changing `.env`.

## Requirements

- Python `3.10+`
- Internet access to the Lift API and an Arc RPC endpoint
- A token image available on disk
- An EVM wallet funded with enough Arc native currency for the live launch fee and gas
- Enough configured `QUOTE_TOKEN` when `INITIAL_BUY` is greater than zero

> [!CAUTION]
> This script signs transactions with a private key. Use a dedicated wallet, never expose `.env`, verify all production addresses, and test with a small amount before committing significant funds.

## Installation

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at least:

```dotenv
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
TOKEN_IMAGE=token.png
```

## Usage

### Launch With `.env` Values

```powershell
python main.py
```

On Windows, the included wrapper forwards all arguments:

```powershell
.\run.bat
```

### Override Token Details

CLI values take precedence over their matching environment variables:

```powershell
python main.py --image .\token.jpg --name "My Token" --symbol MTK
```

| Option | Purpose | Environment fallback |
| --- | --- | --- |
| `--image PATH` | Token image to upload | `TOKEN_IMAGE` |
| `--name TEXT` | Token display name | `TOKEN_NAME` |
| `--symbol TEXT` | Token ticker; normalized to uppercase | `TOKEN_SYMBOL` |
| `--dry-run` | Publish image and metadata without sending transactions | `DRY_RUN` |

View built-in CLI help with `python main.py --help`.

### Dry Run

```powershell
python main.py --dry-run
```

> [!IMPORTANT]
> A dry run still uploads the image and creates **public metadata**. It also connects to Arc, reads factory data, generates a random salt, and predicts an address, but it does not send an approval or launch transaction.

### Initial Buy

Set an amount with no more than six decimal places:

```dotenv
INITIAL_BUY=10.5
MIN_TOKENS_OUT=250000
```

The example converts `10.5` to `10500000` base units. If the wallet's allowance is too low, the launcher confirms an approval before sending the launch.

## Configuration

Copy `.env.example` to `.env`. Values shown below are the application's defaults unless marked as required.

### Wallet and Metadata

| Variable | Default | Description |
| --- | --- | --- |
| `PRIVATE_KEY` | **Required** | Valid 32-byte private key used to sign transactions |
| `TOKEN_IMAGE` | **Required** | Local path to the image uploaded to Lift |
| `TOKEN_NAME` | `DXM` | Token name |
| `TOKEN_SYMBOL` | `DXM` | Token symbol, converted to uppercase |
| `TOKEN_DESCRIPTION` | Empty | Public metadata description |
| `TOKEN_WEBSITE` | Empty | Public project website URL |
| `TOKEN_X` | Empty | Public X/Twitter URL or handle |
| `TOKEN_TELEGRAM` | Empty | Public Telegram URL or handle |

### Network and Contracts

| Variable | Default | Description |
| --- | --- | --- |
| `LIFT_API_URL` | `https://api.lift.fun/api/v1` | Base URL for image and metadata requests |
| `ARC_RPC_URL` | `https://rpc.blockdaemon.mainnet.arc.io` | Arc JSON-RPC endpoint |
| `ARC_CHAIN_ID` | `5042` | Required RPC chain ID |
| `LIFT_FACTORY` | `0x1ca37B3C40e89aaD48b5ad3352269c2293CFD3DA` | Lift V4 factory contract |
| `QUOTE_TOKEN` | `0x44b453d355835ce1269fc11d3fa4161c0dcc0087` | ERC-20 used for the initial buy |

### Launch Settings

| Variable | Default | Description |
| --- | --- | --- |
| `CREATOR_ADDRESS` | Signing wallet | Optional creator address |
| `INITIAL_BUY` | `0` | Initial quote-token amount, with up to 6 decimal places |
| `MIN_TOKENS_OUT` | `0` | Minimum accepted output for the initial buy |
| `CREATOR_TAX_BUY_BPS` | `0` | Creator buy tax from `0` to `10000` basis points |
| `CREATOR_TAX_SELL_BPS` | `0` | Creator sell tax from `0` to `10000` basis points |
| `MIN_HOLDER_BALANCE` | `0` | Minimum holder balance passed to the factory |
| `CREATOR_BASE_TO` | `0` | Factory creator-base destination value from `0` to `255` |
| `GUARDED` | `false` | Enables the factory's guarded launch flag |

### Execution and Gas

| Variable | Default | Description |
| --- | --- | --- |
| `DRY_RUN` | `false` | Disables blockchain writes when true |
| `TX_TIMEOUT` | `180` | Seconds to wait for a transaction receipt |
| `MAX_PRIORITY_FEE_WEI` | `0` | EIP-1559 priority fee in wei |
| `MAX_FEE_PER_GAS_WEI` | Auto | Optional EIP-1559 maximum fee in wei |

Boolean settings accept `true`, `false`, `1`, `0`, `yes`, `no`, `on`, or `off` (case-insensitive).

> [!WARNING]
> `MIN_TOKENS_OUT=0` provides no slippage protection. Choose an appropriate nonzero minimum whenever `INITIAL_BUY` is enabled.

## Output and Safety

Before a blockchain write, the command prints a JSON summary containing the wallet, creator, metadata URI, predicted token address, live launch fee, initial buy, and salt. After confirmation, it prints transaction hashes and the token address.

- Never commit, log, or share `.env` or `PRIVATE_KEY`.
- Confirm the factory, quote token, RPC, and chain ID against [Lift's production configuration](https://lift.fun/config.js).
- Each run uses a **new random salt**, so each predicted token address is different.
- After an uncertain timeout, inspect the wallet's transaction history before rerunning to avoid an unintended duplicate launch.
- API uploads are public and cannot be undone by dry-run mode.
- Review taxes, slippage, recipient settings, balances, and gas values before signing.

## Development

Install runtime and test dependencies:

```powershell
pip install -r requirements-dev.txt
```

Run the test suite:

```powershell
pytest
```

Tests cover amount conversion, default configuration, Lift API request payloads, and the V4 launch function selector.

## Contributing

Contributions are welcome. Keep changes focused and avoid including wallet secrets or generated files.

1. Fork the repository and create a descriptive branch.
2. Install `requirements-dev.txt` in a virtual environment.
3. Implement the change with tests where practical.
4. Run `pytest` and confirm the CLI help still works.
5. Open a pull request describing the behavior, risks, and verification performed.

For contract-related changes, include the source used to verify addresses, ABI entries, selectors, and expected on-chain behavior.

## Disclaimer

This project is independent tooling for interacting with Lift and is provided for educational and operational use. Token launches and on-chain transactions are irreversible and involve financial risk. Review the code and current Lift terms before use. No guarantee of availability, correctness, token performance, or compatibility with future contract versions is provided.

## License

No license file is currently included. Unless the repository owner adds a license, the source remains under default copyright restrictions and may not be copied, modified, or redistributed without permission. Contributors should confirm licensing terms with the repository owner before submitting substantial work.
