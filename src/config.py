"""
Configuration module - loads settings from YAML file and 1Password
"""

import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse, urlunparse

import yaml

logger = logging.getLogger(__name__)

class Config:
    """Application configuration"""
    
    def __init__(self):
        self._config: dict = {}
        self._private_key: Optional[str] = None
        self._trongrid_api_key: Optional[str] = None
        self._database_password: Optional[str] = None
        self._loaded: bool = False
        
    def load_from_yaml(self, config_path: Optional[str] = None) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file. If None:
              1) uses CONFIG_PATH env var if set
              2) else tries <project_root>/config/facilitator.config.yaml
              3) else falls back to <project_root>/facilitator.config.yaml
        
        Raises:
            FileNotFoundError: If configuration file is not found.
        """
        if self._loaded and config_path is None:
            return  # Prevents redundant loading if already loaded with default path
            
        if config_path is None:
            config_path = os.getenv("CONFIG_PATH")
        
        project_root = Path(__file__).parent.parent
        if config_path is None:
            # Prefer config/facilitator.config.yaml if present, else project root
            config_dir_candidate = project_root / "config" / "facilitator.config.yaml"
            if config_dir_candidate.exists():
                config_path = str(config_dir_candidate)
            else:
                config_path = str(project_root / "facilitator.config.yaml")
        
        if not os.path.exists(config_path):
             raise FileNotFoundError(
                 f"Configuration file not found at {config_path}. "
                 "Please ensure facilitator.config.yaml exists in the project root "
                 "or config/ directory, or set CONFIG_PATH environment variable."
             )
        logger.info(f"Configuration file found at {config_path}")
        
        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f) or {}

        self._validate_required()
        self._loaded = True
    
    def _validate_required(self) -> None:
        """
        Validate that required configuration keys are present and non-empty.
        Raises ValueError to force service stop on missing critical config.
        """
        errors = []
        db = self._config.get("database", {})
        if not db.get("url"):
            errors.append("database.url is required and must be non-empty")
        fac = self._config.get("facilitator", {})
        if not fac.get("fee_to_address"):
            errors.append("facilitator.fee_to_address is required and must be non-empty")
        if not fac.get("networks") or not isinstance(fac["networks"], list):
            errors.append("facilitator.networks is required and must be a non-empty list")
        # If no direct private_key, we check for 1Password token
        if not fac.get("private_key"):
            token = self.onepassword_token
            if not token or token == "your-op-token" or token == "your-service-account-token":
                # No 1Password and no direct key -> Error
                errors.append(
                    "Facilitator Key is missing. Provide 'facilitator.private_key' for local dev "
                    "or 'onepassword.token' for production."
                )
            else:
                # Using 1Password, ensure metadata is present
                if not self._config.get("onepassword", {}).get("vault"):
                    errors.append("onepassword.vault is required when using 1Password")
                if not self._config.get("onepassword", {}).get("privatekey_item"):
                    errors.append("onepassword.privatekey_item is required when using 1Password")
        if errors:
            raise ValueError(
                "Configuration validation failed. " + " ".join(errors)
            )
    
    @property
    def database_url(self) -> str:
        """Get database connection URL (may not contain password if using 1Password)"""
        return self._config.get("database", {}).get("url", "")

    @property
    def database_ssl_mode(self) -> str:
        """SSL mode for DB: disable | require | verify-ca | verify-full. Default disable (local)."""
        return self._config.get("database", {}).get("ssl_mode", "disable")

    @property
    def database_max_open_conns(self) -> int:
        """Max total connections in pool (pool_size + max_overflow). Default 25."""
        return int(self._config.get("database", {}).get("max_open_conns", 25))

    @property
    def database_max_idle_conns(self) -> int:
        """Connections to keep open when idle (pool_size). Default 15."""
        return int(self._config.get("database", {}).get("max_idle_conns", 15))

    @property
    def database_max_life_time(self) -> int:
        """Seconds before recycling a connection (pool_recycle). Default 600."""
        return int(self._config.get("database", {}).get("max_life_time", 600))

    @property
    def onepassword_database_password_item(self) -> str:
        """Get 1Password item name for database password"""
        return self._config.get("onepassword", {}).get("database_password_item", "")

    @property
    def onepassword_database_password_field(self) -> str:
        """Get 1Password field name for database password"""
        return self._config.get("onepassword", {}).get("database_password_field", "password")
    
    @property
    def onepassword_vault(self) -> str:
        """Get 1Password vault name"""
        return self._config.get("onepassword", {}).get("vault", "")
    
    @property
    def onepassword_item(self) -> str:
        """Get 1Password item name for private key"""
        return self._config.get("onepassword", {}).get("privatekey_item", "")
    
    @property
    def onepassword_field(self) -> str:
        """Get 1Password field name for private key"""
        return self._config.get("onepassword", {}).get("privatekey_field", "private_key")

    @property
    def onepassword_trongrid_api_key_item(self) -> str:
        """Get 1Password item name for TronGrid API Key"""
        return self._config.get("onepassword", {}).get("trongrid_api_key_item", "")

    @property
    def onepassword_trongrid_api_key_field(self) -> str:
        """Get 1Password field name for TronGrid API Key"""
        return self._config.get("onepassword", {}).get("trongrid_api_key_field", "api_key")
        
    @property
    def onepassword_token(self) -> Optional[str]:
        """
        Get 1Password service account token.
        Priority: 
        1. Environment variable OP_SERVICE_ACCOUNT_TOKEN
        2. Configuration file
        """
        env_token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
        if env_token:
            return env_token
        return self._config.get("onepassword", {}).get("token")
    
    @property
    def fee_to_address(self) -> str:
        """Get fee recipient address"""
        return self._config.get("facilitator", {}).get("fee_to_address", "")
    
    @property
    def base_fee(self) -> dict[str, int]:
        """
        Get base fee per token (symbol -> amount in smallest units).

        YAML format:
          base_fee:
            USDT: 100          # 0.0001 USDT (6 decimals)
            USDD: 100000000000000  # 0.0001 USDD (18 decimals)

        Legacy: single string/number is treated as USDT fee for backward compat.
        """
        val = self._config.get("facilitator", {}).get("base_fee", {})
        if isinstance(val, dict):
            return {k: int(v) for k, v in val.items()}
        if isinstance(val, (str, int)):
            return {"USDT": int(val)}
        return {}
    
    @property
    def networks(self) -> list[str]:
        """Get supported networks"""
        return self._config.get("facilitator", {}).get("networks", [])
    
    @property
    def server_host(self) -> str:
        """Get server host"""
        return self._config.get("server", {}).get("host", "0.0.0.0")

    @property
    def server_port(self) -> int:
        """Get server port"""
        return self._config.get("server", {}).get("port", 8001)

    @property
    def server_workers(self) -> int:
        """Get uvicorn workers (default 1). Use 2+ for higher settle QPS headroom."""
        return int(self._config.get("server", {}).get("workers", 1))

    @property
    def logging_config(self) -> dict:
        """Get logging configuration"""
        return self._config.get("logging", {})

    @property
    def api_key_refresh_interval(self) -> int:
        """Get API key refresh interval in seconds"""
        return self._config.get("rate_limit", {}).get("api_key_refresh_interval", 60)

    @property
    def rate_limit_authenticated(self) -> str:
        """Get rate limit for authenticated users"""
        return self._config.get("rate_limit", {}).get("authenticated", "1000/minute")

    @property
    def rate_limit_anonymous(self) -> str:
        """Get rate limit for anonymous users"""
        return self._config.get("rate_limit", {}).get("anonymous", "1/minute")

    @property
    def monitoring_port(self) -> int:
        """Get monitoring port, defaults to server port if not specified"""
        return self._config.get("monitoring", {}).get("port", self.server_port)

    @property
    def monitoring_endpoint(self) -> str:
        """Get monitoring endpoint path"""
        return self._config.get("monitoring", {}).get("endpoint", "/metrics")

    async def get_private_key(self) -> str:
        """
        Get private key. 
        Priority:
        1. Cached value
        2. Direct 'private_key' in YAML (for local dev)
        3. 1Password retrieval
        
        Returns:
            Private key string
        """
        if self._private_key is not None:
            return self._private_key
            
        # 1. Try direct key from YAML first (fallback for local dev)
        direct_key = self._config.get("facilitator", {}).get("private_key")
        if direct_key:
            self._private_key = direct_key
            return self._private_key
        
        # 2. Prevent using placeholder 1Password token
        token = self.onepassword_token
        if not token or token == "your-op-token":
            raise ValueError(
                "Facilitator Private Key is not configured.\n\n"
                "Please choose one of the following methods in 'facilitator.config.yaml':\n"
                "  A) Local Dev: Uncomment 'private_key' under the 'facilitator' section and fill it.\n"
                "  B) Production: Fill in a valid 1Password Service Account Token under 'onepassword.token'.\n"
            )

        # 3. Fallback to 1Password
        from onepassword_client import get_secret_from_1password
        
        self._private_key = await get_secret_from_1password(
            vault=self.onepassword_vault,
            item=self.onepassword_item,
            field=self.onepassword_field,
            token=token,
        )
        return self._private_key

    async def get_trongrid_api_key(self) -> Optional[str]:
        """
        Get TronGrid API Key.
        Priority:
        1. Cached value
        2. Environment variable TRON_GRID_API_KEY
        3. Direct 'trongrid_api_key' in YAML (local dev)
        4. 1Password retrieval
        
        Returns:
            API Key string or None if not configured
        """
        if self._trongrid_api_key is not None:
            return self._trongrid_api_key
            
        # 1. Try environment variable first
        env_key = os.getenv("TRON_GRID_API_KEY")
        if env_key:
            self._trongrid_api_key = env_key
            return self._trongrid_api_key
            
        # 2. Try direct key from YAML (fallback for local dev)
        direct_key = self._config.get("facilitator", {}).get("trongrid_api_key")
        if direct_key:
            self._trongrid_api_key = direct_key
            return self._trongrid_api_key

        # 3. Try 1Password if configured
        item = self.onepassword_trongrid_api_key_item
        token = self.onepassword_token
        
        if item and token and token != "your-op-token" and token != "your-service-account-token":
            try:
                from onepassword_client import get_secret_from_1password
                self._trongrid_api_key = await get_secret_from_1password(
                    vault=self.onepassword_vault,
                    item=item,
                    field=self.onepassword_trongrid_api_key_field,
                    token=token,
                )
                return self._trongrid_api_key
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load TronGrid API Key from 1Password: {e}")
        
        return None

    async def get_database_password(self) -> Optional[str]:
        """
        Get database password.
        Priority:
        1. Cached value
        2. Direct database.password in YAML (local dev)
        3. 1Password retrieval (when onepassword.database_password_item is set)

        Returns:
            Password string, or None if not configured (URL may contain password or no auth)
        """
        if self._database_password is not None:
            return self._database_password

        # 1. Direct password in config (local dev)
        direct = self._config.get("database", {}).get("password")
        if direct is not None and direct != "":
            self._database_password = str(direct)
            return self._database_password

        # 2. 1Password
        item = self.onepassword_database_password_item
        token = self.onepassword_token
        if not item or not token or token in ("your-op-token", "your-service-account-token"):
            return None

        from onepassword_client import get_secret_from_1password
        self._database_password = await get_secret_from_1password(
            vault=self.onepassword_vault,
            item=item,
            field=self.onepassword_database_password_field,
            token=token,
        )
        return self._database_password

    async def get_database_url(self) -> str:
        """
        Get database connection URL, with password injected when available.

        Password is fetched from database.password (config) or 1Password (when database_password_item is set),
        then injected into database.url (URL may be without password, e.g. postgresql+asyncpg://user@host:5432/db).
        """
        raw_url = self._config.get("database", {}).get("url", "")
        if not raw_url:
            raise ValueError("database.url is required")

        password = await self.get_database_password()
        if not password:
            return raw_url

        # Inject password into URL (password may contain special chars)
        parsed = urlparse(raw_url)
        username = parsed.username or ""
        port = f":{parsed.port}" if parsed.port else ""
        quoted = quote(password, safe="")
        netloc = f"{username}:{quoted}@{parsed.hostname or ''}{port}"
        return urlunparse(parsed._replace(netloc=netloc))


# Global config instance
config = Config()
