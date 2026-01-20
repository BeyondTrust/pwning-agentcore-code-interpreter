"""Configuration management for C2 toolkit."""

import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """
    Configuration loaded from environment variables or .env file.

    Environment variables (set by Terraform or .env file):
    - EC2_IP: Public IP of C2 server
    - DOMAIN: C2 DNS domain (e.g., c2.bt-research-control.com)
    - EC2_INSTANCE_ID: For AWS SSM access
    - S3_BUCKET: S3 bucket for artifacts
    """

    def __init__(self, env_file: str = None):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file (auto-detected if not specified)
        """
        # Auto-detect .env file location
        if env_file is None:
            # Try current directory, then package root
            candidates = [
                Path.cwd() / ".env",
                Path(__file__).parent.parent.parent / ".env",
            ]
            for candidate in candidates:
                if candidate.exists():
                    env_file = str(candidate)
                    break

        # Load .env file if found
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)

        # Load configuration from environment
        self.ec2_ip = os.environ.get("EC2_IP", "localhost")
        self.domain = os.environ.get("DOMAIN", "c2.bt-research-control.com")
        self.ec2_instance_id = os.environ.get("EC2_INSTANCE_ID")
        self.s3_bucket = os.environ.get("S3_BUCKET")

        # Derived settings
        self.c2_server_url = f"http://{self.ec2_ip}:8080"

    @property
    def is_configured(self) -> bool:
        """Check if essential configuration is present."""
        return self.ec2_ip != "localhost" and self.domain != ""

    def __repr__(self) -> str:
        return (
            f"Config(ec2_ip={self.ec2_ip!r}, domain={self.domain!r}, "
            f"c2_server_url={self.c2_server_url!r})"
        )


# Global config instance (lazy-loaded)
_config = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
