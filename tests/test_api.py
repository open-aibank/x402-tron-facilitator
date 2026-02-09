
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Minimal valid settle request body (matches x402_tron SettleRequest / PaymentPayload shape)
SETTLE_BODY = {
    "paymentPayload": {
        "x402Version": 1,
        "accepted": {
            "scheme": "tron",
            "network": "mainnet",
            "amount": "0",
            "asset": "USDT",
            "payTo": "TXxx0000000000000000000000000000000",
        },
        "payload": {
            "signature": "0x",
            "paymentPermit": {
                "meta": {
                    "kind": "PAYMENT_ONLY",
                    "paymentId": "pay-123",
                    "nonce": "0",
                    "validAfter": 0,
                    "validBefore": 9999999999,
                },
                "buyer": "TXxx0000000000000000000000000000000",
                "caller": "TXxx0000000000000000000000000000000",
                "payment": {"payToken": "USDT", "payAmount": "0", "payTo": "TXxx0000000000000000000000000000000"},
                "fee": {"feeTo": "TXxx0000000000000000000000000000000", "feeAmount": "0"},
                "delivery": {
                    "receiveToken": "USDT",
                    "miniReceiveAmount": "0",
                    "tokenId": "0",
                },
            },
        },
    },
    "paymentRequirements": {
        "scheme": "tron",
        "network": "mainnet",
        "amount": "0",
        "asset": "USDT",
        "payTo": "TXxx0000000000000000000000000000000",
    },
}


@pytest.mark.asyncio
async def test_health(client):
    """Test /health endpoint (no rate limit)"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health(client):
    """Test /health endpoint (no rate limit)"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_supported(client, mocker):
    """Test /supported endpoint"""
    # Mock x402_facilitator.supported
    mock_supported = mocker.patch("main.x402_facilitator.supported", return_value={"pricing": "flat"})
    
    response = await client.get("/supported")
    assert response.status_code == 200
    assert response.json() == {"pricing": "flat"}

@pytest.mark.asyncio
async def test_get_payment_success(client, mock_db):
    """Test /payments/{payment_id} endpoint - Success state"""
    # Mock database record
    mock_record = MagicMock()
    mock_record.payment_id = "pay-123"
    mock_record.tx_hash = "0xhash"
    mock_record.status = "success"
    mock_record.created_at = datetime.now()
    
    mock_db["get"].return_value = mock_record
    
    response = await client.get("/payments/pay-123")
    assert response.status_code == 200
    data = response.json()
    assert data["paymentId"] == "pay-123"
    assert data["txHash"] == "0xhash"

@pytest.mark.asyncio
async def test_get_payment_not_found(client, mock_db):
    """Test /payments/{payment_id} endpoint - Not found state"""
    mock_db["get"].return_value = None
    
    response = await client.get("/payments/non-existent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"

@pytest.mark.asyncio
async def test_rate_limiting_trigger(client, mocker):
    """Verify rate limiting on /settle (Anonymous user 1/min): first 200, second 429."""
    from x402_tron.types import SettleResponse

    mocker.patch("auth.get_remote_address", return_value="1.2.3.4")
    mocker.patch(
        "main.x402_facilitator.settle",
        new_callable=AsyncMock,
        return_value=SettleResponse(success=True, transaction="0xtx"),
    )
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("main.get_session", return_value=mock_session)
    mock_record = MagicMock()
    mock_record.tx_hash = ""
    mock_record.status = "pending"
    mocker.patch(
        "main.insert_payment_record_pending",
        new_callable=AsyncMock,
        return_value=mock_record,
    )

    resp1 = await client.post("/settle", json=SETTLE_BODY)
    assert resp1.status_code == 200

    resp2 = await client.post("/settle", json=SETTLE_BODY)
    assert resp2.status_code == 429
    assert "Rate limit exceeded" in resp2.json()["error"]


# --- Settle flow tests (insert pending -> settle -> update & commit / rollback) ---


@pytest.mark.asyncio
async def test_settle_success_with_payment_id(client, mocker):
    """Settle with payment_id: insert pending -> settle succeeds -> update & commit -> 200."""
    mocker.patch("auth.get_remote_address", return_value="127.0.0.1")
    mocker.patch("main._get_payment_id_from_request", return_value="pay-123")
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("main.get_session", return_value=mock_session)

    mock_record = MagicMock()
    mock_record.tx_hash = ""
    mock_record.status = "pending"
    mocker.patch(
        "main.insert_payment_record_pending",
        new_callable=AsyncMock,
        return_value=mock_record,
    )

    from x402_tron.types import SettleResponse
    mocker.patch(
        "main.x402_facilitator.settle",
        new_callable=AsyncMock,
        return_value=SettleResponse(success=True, transaction="0xtxhash"),
    )

    response = await client.post("/settle", json=SETTLE_BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["transaction"] == "0xtxhash"
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_called()
    assert mock_record.tx_hash == "0xtxhash"
    assert mock_record.status == "success"


@pytest.mark.asyncio
async def test_settle_no_payment_id_calls_settle_only(client, mocker):
    """Settle without payment_id: no DB; settle only -> 200."""
    from x402_tron.types import SettleResponse
    mocker.patch("auth.get_remote_address", return_value="127.0.0.2")
    mocker.patch("main._get_payment_id_from_request", return_value=None)
    mocker.patch(
        "main.x402_facilitator.settle",
        new_callable=AsyncMock,
        return_value=SettleResponse(success=True, transaction="0xtxhash"),
    )
    get_session_patch = mocker.patch("main.get_session")

    response = await client.post("/settle", json=SETTLE_BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    get_session_patch.assert_not_called()


@pytest.mark.asyncio
async def test_settle_integrity_error_returns_409_with_existing_success(client, mocker):
    """Insert raises IntegrityError (duplicate payment_id); existing success -> 409 with body."""
    mocker.patch("auth.get_remote_address", return_value="127.0.0.3")
    mocker.patch("main._get_payment_id_from_request", return_value="pay-123")
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("main.get_session", return_value=mock_session)
    from sqlalchemy.exc import IntegrityError
    mocker.patch(
        "main.insert_payment_record_pending",
        new_callable=AsyncMock,
        side_effect=IntegrityError("stmt", "params", "orig"),
    )
    mock_existing = MagicMock()
    mock_existing.status = "success"
    mock_existing.tx_hash = "0xexisting"
    mocker.patch("main.get_payment_by_id", new_callable=AsyncMock, return_value=mock_existing)

    response = await client.post("/settle", json=SETTLE_BODY)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "payment_id already processed"
    assert detail["success"] is True
    assert detail["transaction"] == "0xexisting"
    assert detail["payment_id"] == "pay-123"
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_settle_integrity_error_returns_409_no_success_record(client, mocker):
    """Insert raises IntegrityError; no existing success record -> 409 with body."""
    mocker.patch("auth.get_remote_address", return_value="127.0.0.4")
    mocker.patch("main._get_payment_id_from_request", return_value="pay-123")
    mock_session = MagicMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("main.get_session", return_value=mock_session)
    from sqlalchemy.exc import IntegrityError
    mocker.patch(
        "main.insert_payment_record_pending",
        new_callable=AsyncMock,
        side_effect=IntegrityError("stmt", "params", "orig"),
    )
    mocker.patch("main.get_payment_by_id", new_callable=AsyncMock, return_value=None)

    response = await client.post("/settle", json=SETTLE_BODY)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "payment_id already processed"
    assert detail["success"] is False
    assert detail["transaction"] is None
    assert detail["payment_id"] == "pay-123"


@pytest.mark.asyncio
async def test_settle_failure_rollback_no_record(client, mocker):
    """Settle raises -> rollback -> 500; no record persisted."""
    mocker.patch("auth.get_remote_address", return_value="127.0.0.5")
    mocker.patch("main._get_payment_id_from_request", return_value="pay-123")
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("main.get_session", return_value=mock_session)

    mock_record = MagicMock()
    mock_record.tx_hash = ""
    mock_record.status = "pending"
    mocker.patch(
        "main.insert_payment_record_pending",
        new_callable=AsyncMock,
        return_value=mock_record,
    )
    mocker.patch(
        "main.x402_facilitator.settle",
        new_callable=AsyncMock,
        side_effect=Exception("chain error"),
    )

    response = await client.post("/settle", json=SETTLE_BODY)
    assert response.status_code == 500
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
