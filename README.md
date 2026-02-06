# X402 TRON Facilitator

X402 TRON Facilitator is a service designed to facilitate the **X402 (HTTP 402 Payment Required)** protocol on the TRON blockchain. It provides a standard interface for backend services to handle off-chain payment verification and on-chain settlement, enabling seamless "Pay-as-you-go" mechanisms for digital resources.

## 🚀 Key Features

- **Multi-Network Support**: Compatible with TRON Mainnet, Nile Testnet, and Shasta Testnet.
- **Payment Verification**: Robust verification of payment payloads off-chain.
- **On-chain Settlement**: Handles the complexity of settling payments directly on the TRON blockchain.
- **Dynamic Fee Quoting**: Provides real-time fee quotes based on payment requirements.
- **FastAPI Powered**: High-performance, production-ready REST API.

## 📋 Prerequisites

- Python 3.10 or higher
- A TRON account with a private key (for signing and settling transactions)
- Node/RPC access for TRON networks (handled via `x402-tron` package)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/open-aibank/x402-tron-facilitator.git
   cd x402-tron-facilitator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy the example environment file and fill in your details:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   - `PRIVATE_KEY`: Your TRON private key (used for settlement).
   - `FEE_TO_ADDRESS`: The TRON address that will receive the fees.
   - `BASE_FEE`: The base fee amount (Sun for TRX, or scaled for tokens).
   - `TRON_GRID_API_KEY`: TronGrid API key for TRON RPC access (required for reliable on-chain reads/writes, especially on `tron:mainnet`).

   Notes:
   - If you enable `tron:mainnet`, the facilitator relies on TronGrid (or another TRON JSON-RPC endpoint) to build and broadcast transactions.
   - Without a valid `TRON_GRID_API_KEY`, requests may fail with HTTP `429 Too Many Requests` due to rate limiting.

## 🏃 Running the Facilitator

Start the server using the provided entry point:

```bash
python src/main.py
```

The server will start at `http://0.0.0.0:8001` by default.

## 🏗️ Architecture

The facilitator acts as a bridge between the client (which holds the payment proof) and the blockchain. It uses the `x402-tron` library to:
1.  **Validate** signatures and permits.
2.  **Verify** that the payment amount and recipient match the expectations.
3.  **Broadcast** the transaction to the TRON network to move funds.

---

Built with ❤️ by the **Open AI Bank** team.
