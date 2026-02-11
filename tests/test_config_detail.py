"""
Detailed unit tests for config changes: _network_config, get_fee_to_address,
get_base_fee, _validate_required, get_private_key (per-network + 1Password fallback).
"""
import pytest
from unittest.mock import AsyncMock, patch

from config import Config


# ---- _network_config ----
def test_network_config_returns_empty_when_no_facilitator():
    config = Config()
    config._config = {}
    assert config._network_config("tron:nile") == {}


def test_network_config_returns_empty_when_no_networks_key():
    config = Config()
    config._config = {"facilitator": {}}
    assert config._network_config("tron:nile") == {}


def test_network_config_returns_empty_when_network_id_unknown():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T..."},
            }
        }
    }
    assert config._network_config("tron:mainnet") == {}
    assert config._network_config("unknown:net") == {}


def test_network_config_returns_empty_when_network_value_is_none():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": None,
            }
        }
    }
    # .get(network_id) returns None, then "or {}" gives {}
    assert config._network_config("tron:nile") == {}


def test_network_config_returns_dict_when_present():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "TNile123", "base_fee": {"USDT": 100}},
            }
        }
    }
    out = config._network_config("tron:nile")
    assert out == {"fee_to_address": "TNile123", "base_fee": {"USDT": 100}}


# ---- get_fee_to_address ----
def test_get_fee_to_address_returns_empty_for_unknown_network():
    config = Config()
    config._config = {"facilitator": {"networks": {"tron:nile": {"fee_to_address": "T..."}}}}
    assert config.get_fee_to_address("tron:mainnet") == ""


def test_get_fee_to_address_returns_default_empty_when_key_missing():
    config = Config()
    config._config = {"facilitator": {"networks": {"tron:nile": {"base_fee": {}}}}}
    assert config.get_fee_to_address("tron:nile") == ""


def test_get_fee_to_address_returns_value_when_present():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {"tron:nile": {"fee_to_address": "TNileFeeTo123456789012345678901234"}}
        }
    }
    assert config.get_fee_to_address("tron:nile") == "TNileFeeTo123456789012345678901234"


# ---- get_base_fee ----
def test_get_base_fee_returns_empty_dict_for_unknown_network():
    config = Config()
    config._config = {"facilitator": {"networks": {"tron:nile": {"base_fee": {"USDT": 100}}}}}
    assert config.get_base_fee("tron:mainnet") == {}


def test_get_base_fee_returns_empty_dict_when_base_fee_missing():
    config = Config()
    config._config = {"facilitator": {"networks": {"tron:nile": {"fee_to_address": "T..."}}}}
    assert config.get_base_fee("tron:nile") == {}


def test_get_base_fee_returns_dict_with_int_values():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"base_fee": {"USDT": 100, "USDD": 200000000000000}},
            }
        }
    }
    assert config.get_base_fee("tron:nile") == {"USDT": 100, "USDD": 200000000000000}


def test_get_base_fee_legacy_single_int_treated_as_usdt():
    config = Config()
    config._config = {
        "facilitator": {"networks": {"tron:nile": {"base_fee": 150}}}
    }
    assert config.get_base_fee("tron:nile") == {"USDT": 150}


def test_get_base_fee_legacy_single_string_treated_as_usdt():
    config = Config()
    config._config = {
        "facilitator": {"networks": {"tron:nile": {"base_fee": "200"}}}
    }
    assert config.get_base_fee("tron:nile") == {"USDT": 200}


# ---- _validate_required ----
def test_validate_required_raises_when_database_url_missing():
    config = Config()
    config._config = {
        "database": {},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": "x" * 64},
            }
        },
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "database.url" in str(exc_info.value)


def test_validate_required_raises_when_networks_missing():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {},
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "facilitator.networks" in str(exc_info.value)


def test_validate_required_raises_when_networks_not_dict():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {"networks": ["tron:nile"]},
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "facilitator.networks" in str(exc_info.value)
    assert "dict" in str(exc_info.value).lower()


def test_validate_required_raises_when_networks_empty_dict():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {"networks": {}},
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "facilitator.networks" in str(exc_info.value)


def test_validate_required_raises_when_network_missing_fee_to_address():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "", "private_key": "a" * 64},
            }
        },
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "fee_to_address" in str(exc_info.value)
    assert "tron:nile" in str(exc_info.value)


def test_validate_required_raises_when_network_missing_private_key_and_no_op():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": ""},
            }
        },
        "onepassword": {},
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "private_key" in str(exc_info.value)
    assert "tron:nile" in str(exc_info.value)


def test_validate_required_passes_when_all_required_present():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "TNile123", "private_key": "a" * 64},
            }
        },
    }
    config._validate_required()  # no raise


def test_validate_required_passes_when_network_no_private_key_but_has_op():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "TNile123", "private_key": ""},
            }
        },
        "onepassword": {
            "token": "real-op-token",
            "tron_nile_private_key": "V/Item/private_key",
        },
    }
    config._validate_required()  # no raise


def test_validate_required_raises_when_op_token_placeholder():
    config = Config()
    config._config = {
        "database": {"url": "postgresql://localhost/db"},
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": ""},
            }
        },
        "onepassword": {
            "token": "your-op-token",
            "tron_nile_private_key": "V/Item/private_key",
        },
    }
    with pytest.raises(ValueError) as exc_info:
        config._validate_required()
    assert "private_key" in str(exc_info.value)


# ---- get_private_key: per-network + fallback ----
@pytest.mark.asyncio
async def test_get_private_key_returns_network_key_when_present():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": "  my-hex-key  "},
            }
        }
    }
    key = await config.get_private_key("tron:nile")
    assert key == "my-hex-key"


@pytest.mark.asyncio
async def test_get_private_key_returns_cached_fallback_after_first_op_fetch():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": "key-nile"},
                "tron:mainnet": {"fee_to_address": "T...", "private_key": ""},
            }
        },
        "onepassword": {"token": "t", "tron_mainnet_private_key": "V/I/private_key"},
    }
    with patch("onepassword_client.get_secret_from_1password", new_callable=AsyncMock, return_value="op-fetched-key"):
        key_mainnet = await config.get_private_key("tron:mainnet")
    assert key_mainnet == "op-fetched-key"
    # Second call for same network uses cache
    key_mainnet2 = await config.get_private_key("tron:mainnet")
    assert key_mainnet2 == "op-fetched-key"


@pytest.mark.asyncio
async def test_get_private_key_raises_when_no_key_and_no_op():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": ""},
            }
        },
        "onepassword": {},
    }
    with pytest.raises(ValueError) as exc_info:
        await config.get_private_key("tron:nile")
    assert "tron:nile" in str(exc_info.value)
    assert "not configured" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_private_key_raises_when_token_is_placeholder():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": ""},
            }
        },
        "onepassword": {"token": "your-op-token", "tron_nile_private_key": "V/I/private_key"},
    }
    with pytest.raises(ValueError) as exc_info:
        await config.get_private_key("tron:nile")
    assert "not configured" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_private_key_per_network_takes_precedence_over_cached_op():
    config = Config()
    config._private_key_cache["tron:nile"] = "cached-op-key"
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T...", "private_key": "nile-direct-key"},
            }
        },
    }
    key = await config.get_private_key("tron:nile")
    assert key == "nile-direct-key"


# ---- networks property (list of keys) ----
def test_networks_returns_list_of_keys():
    config = Config()
    config._config = {
        "facilitator": {
            "networks": {
                "tron:nile": {"fee_to_address": "T..."},
                "tron:mainnet": {"fee_to_address": "T..."},
            }
        }
    }
    nets = config.networks
    assert set(nets) == {"tron:nile", "tron:mainnet"}
    assert len(nets) == 2


def test_networks_returns_empty_when_not_dict():
    config = Config()
    config._config = {"facilitator": {"networks": ["tron:nile"]}}
    assert config.networks == []
