"""Configuration management for S3 C2 toolkit."""

import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """
    Configuration loaded from environment variables or .env file.
    Environment variables (set by Terraform or .env file):
    - S3_C2_BUCKET: S3 bucket for S3 C2 channel sessions
    - AWS_REGION: AWS region (default: us-east-1)
    """

    def __init__(self, env_file: str = None):
        if env_file is None:
            candidates = [
                Path.cwd() / ".env",
                Path(__file__).parent.parent.parent / ".env",
                ]
            for candidate in candidates:
                if candidate.exists():
                    env_file = str(candidate)
                    break

        if env_file and Path(env_file).exists():
            load_dotenv(env_file)

        self.s3_c2_bucket = os.environ.get("S3_C2_BUCKET")
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")

    @property
    def is_configured(self) -> bool:
        """Check if essential configuration is present."""
        return self.s3_c2_bucket is not None

    def __repr__(self) -> str:
        return (
            f"Config(s3_c2_bucket={self.s3_c2_bucket!r}, "
            f"aws_region={self.aws_region!r})"
        )


_config = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
