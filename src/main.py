"""
Facilitator Main Entry Point
Starts a FastAPI server for facilitator operations with full payment flow support.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from x402_tron.logging_config import setup_logging
from x402_tron.mechanisms.facilitator import UptoTronFacilitatorMechanism
from x402_tron.signers.facilitator import TronFacilitatorSigner
from x402_tron.facilitator.x402_facilitator import X402Facilitator
from x402_tron.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    SettleResponse,
    FeeQuoteResponse,
)
from pydantic import BaseModel
import config


class VerifyRequest(BaseModel):
    """Verify request model"""
    paymentPayload: PaymentPayload
    paymentRequirements: PaymentRequirements


class SettleRequest(BaseModel):
    """Settle request model"""
    paymentPayload: PaymentPayload
    paymentRequirements: PaymentRequirements


class FeeQuoteRequest(BaseModel):
    """Fee quote request model"""
    accept: PaymentRequirements
    paymentPermitContext: dict | None = None

# Setup logging
setup_logging()

networks = ["tron:nile", "tron:mainnet", "tron:shasta"]
FACILITATOR_HOST = "0.0.0.0"
FACILITATOR_PORT = 8001

# Init app
app = FastAPI(
    title="X402 Facilitator",
    description="Facilitator service for X402 payment protocol",
    version="1.0.0",
)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
x402_facilitator = X402Facilitator()

for network in networks:
    # Initialize facilitator
    facilitator_signer = TronFacilitatorSigner.from_private_key(
        private_key=config.PRIVATE_KEY,
        network=network,
    )
    facilitator_address = facilitator_signer.get_address()
    facilitator_mechanism = UptoTronFacilitatorMechanism(
        facilitator_signer,
        fee_to=config.FEE_TO_ADDRESS,
        base_fee=config.BASE_FEE,
    )
    x402_facilitator.register(network, facilitator_mechanism)

@app.get("/supported")
async def supported():
    """Get supported capabilities"""
    return x402_facilitator.supported()

@app.post("/fee/quote", response_model=FeeQuoteResponse)
async def fee_quote(request: FeeQuoteRequest):
    """
    Get fee quote for payment requirements
    
    Args:
        request: Fee quote request with payment requirements
        
    Returns:
        Fee quote response with fee details
    """
    print(f"{request}")
    return await x402_facilitator.fee_quote(request.accept)

@app.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest):
    """
    Verify payment payload
    
    Args:
        request: Verify request with payment payload and requirements
        
    Returns:
        Verification result
    """
    return await x402_facilitator.verify(request.paymentPayload, request.paymentRequirements)

@app.post("/settle", response_model=SettleResponse)
async def settle(request: SettleRequest):
    """
    Settle payment on-chain
    
    Args:
        request: Settle request with payment payload and requirements
        
    Returns:
        Settlement result with transaction hash
    """
    return await x402_facilitator.settle(request.paymentPayload, request.paymentRequirements)

def main():
    """Start the facilitator server"""
    print("Starting X402 Facilitator Server")
    
    uvicorn.run(
        app,
        host=FACILITATOR_HOST,
        port=FACILITATOR_PORT,
        log_level="info",
    )

if __name__ == "__main__":
    main()
