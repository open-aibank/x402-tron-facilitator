# X402 TRON Facilitator

X402 TRON Facilitator is a service designed to facilitate the **X402 (HTTP 402 Payment Required)** protocol on the TRON blockchain. It provides a standard interface for backend services to handle off-chain payment verification and on-chain settlement, enabling seamless "Pay-as-you-go" mechanisms for digital resources.

## 🚀 Key Features

- **Multi-Network Support**: Compatible with TRON Mainnet, Nile Testnet, and 
Shasta Testnet.
- **Payment Verification**: Robust verification of payment payloads off-chain.
- **On-chain Settlement**: Handles the complexity of settling payments directly 
on the TRON blockchain.
- **Dynamic Fee Quoting**: Provides real-time fee quotes based on payment 
requirements.
- **FastAPI Powered**: High-performance, production-ready REST API.
- **API Key Authentication**: X-API-KEY header support with tiered rate limiting
- **1Password Integration**: Store private key, database password, and other secrets in 1Password

## Prerequisites

- Python 3.10+
- PostgreSQL database
- TRON wallet private key (for settlement signing)
- 1Password or local config (private key, database password, etc.)

## Configuration

Config file: `config/facilitator.config.yaml`. See `config/facilitator.config.example.yaml` for reference.

### Required

```yaml
database:
  url: ""
  password: "your_password"   # Local dev: set directly; or use database_password_item for 1Password

facilitator:
  fee_to_address: "T..."      # Fee recipient address
  private_key: "hex..."       # Local dev; or configure 1Password
  networks: [nile, shasta, mainnet]
```

### Secrets: 1Password or Local

- **Private Key**: `facilitator.private_key` or `onepassword.privatekey_item`
- **Database Password**: `database.password` or `onepassword.database_password_item`
- **TronGrid API Key**: `facilitator.trongrid_api_key` or `onepassword.trongrid_api_key_item`

Configure environment variable `OP_SERVICE_ACCOUNT_TOKEN` when using 1Password.

### Database Connection Pool (Optional)

```yaml
database:
  ssl_mode: "disable"     # disable | require | verify-ca | verify-full
  max_open_conns: 25
  max_idle_conns: 15
  max_life_time: 600
```

## Installation & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp config/facilitator.config.example.yaml config/facilitator.config.yaml

# Start
python src/main.py
```

Listens on `http://0.0.0.0:8001` by default.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/supported` | Supported network/scheme and fee info |
| POST | `/fee/quote` | Get payment fee quote |
| POST | `/verify` | Off-chain verification of payment signature |
| POST | `/settle` | On-chain settlement |
| GET | `/payments/{payment_id}` | Query settlement records by payment ID (returns list, optionally filtered by API key's seller) |
| GET | `/payments/tx/{tx_hash}` | Query settlement records by transaction hash (returns list, optionally filtered by API key's seller) |
| GET | `/health` | Health check |

Both payment query endpoints return a JSON array of `PaymentRecordResponse` objects, ordered from latest to oldest.  
Each record includes:

- `paymentId`: Payment identifier (may be `null` if unavailable)
- `txHash`: Transaction hash
- `status`: `"success"` or `"failed"`
- `createdAt`: Record creation timestamp (ISO 8601)
- `sellerId`: Seller identifier associated with the API key (may be `null`)
- `network`: Network identifier (e.g. `mainnet`, `nile`, `shasta`; may be `null`)

## API Key Authentication

Callers must include `X-API-KEY` in request headers, matching a key in the `api_keys` table. Authenticated requests use `rate_limit_authenticated`; anonymous requests use `rate_limit_anonymous`.

### Adding an API Key

The `sellers` and `api_keys` tables are created automatically on first startup.

To onboard a new client:

1. Insert a row into `sellers` with a unique `seller_id`.
2. Insert one or more rows into `api_keys` with the same `seller_id` and distinct `key` values.

Payment query endpoints will automatically scope results to the `seller_id` associated with the provided `X-API-KEY`.

## Docker

```bash
# Build
docker build -t x402-facilitator .

# Run (mount config)
docker run -p 8001:8001 \
  -e OP_SERVICE_ACCOUNT_TOKEN="" \
  -v $(pwd)/config/facilitator.config.yaml:/app/config/facilitator.config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  x402-facilitator
```

Images are published to [Docker Hub](https://hub.docker.com/u/bankofai) as `bankofai/x402-tron-facilitator`. CI builds on push to main/master or `v*` tags.

## Logging

Logs are written to `logs/x402-facilitator.{date}_{time}.log`, with a new file per startup. 

## Caller Configuration

Servers calling the facilitator (e.g. x402-tron-demo server) must configure:

- `FACILITATOR_URL`: Facilitator URL, **use https** 
- `FACILITATOR_API_KEY`: Key that exists in the facilitator's `api_keys` table

## Project Structure

```
x402-tron-facilitator/
├── config/           # Config examples
├── scripts/          # register_seller and other scripts
├── src/              # Source code
│   ├── main.py       # Entry point
│   ├── config.py     # Config loading
│   ├── database.py   # Database
│   ├── auth.py       # API Key & rate limiting
│   └── ...
├── Dockerfile
└── requirements.txt
```

---

Built with ❤️ by the **Open AI Bank** team.
