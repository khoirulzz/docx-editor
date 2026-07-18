import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

# Load .env file if available
load_dotenv()

class Settings(BaseModel):
    APP_ENV: str = Field(default="development")
    APP_BASE_URL: str = Field(default="http://localhost:7860")
    SESSION_TTL_HOURS: int = Field(default=24, ge=1)
    
    # Archive and upload limits (Security & Threat model)
    MAX_UPLOAD_BYTES: int = Field(default=52_428_800, ge=1024)  # 50 MB
    MAX_SESSION_UPLOAD_BYTES: int = Field(default=209_715_200, ge=1024)  # 200 MB
    MAX_ZIP_ENTRIES: int = Field(default=5000, ge=1)
    MAX_UNCOMPRESSED_BYTES: int = Field(default=524_288_000, ge=1024)  # 500 MB
    MAX_COMPRESSION_RATIO: int = Field(default=100, ge=1)
    MAX_XML_PART_BYTES: int = Field(default=104_857_600, ge=1024)  # 100 MB
    
    # LLM & Resolver configuration
    BLACKBOX_API_KEY: str = Field(default="")
    BLACKBOX_API_BASE: str = Field(default="https://api.blackbox.ai")
    BLACKBOX_MODEL: str = Field(default="blackboxai/deepseek/deepseek-v4-pro")
    BLACKBOX_ZDR_REQUIRED: bool = Field(default=True)
    CROSSREF_MAILTO: str = Field(default="")
    
    # Storage configuration
    STORAGE_BACKEND: str = Field(default="local")
    LOCAL_STORAGE_PATH: str = Field(default="/tmp/ai-docx-editor")
    
    # Feature flags (Capability gates)
    ENABLE_NATIVE_MENDELEY_LEGACY: bool = Field(default=False)
    ENABLE_NATIVE_MENDELEY_CITE: bool = Field(default=False)
    ENABLE_CONTENT_DEBUG_LOGGING: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_security_constraints(self) -> "Settings":
        if self.ENABLE_CONTENT_DEBUG_LOGGING and self.APP_ENV == "production":
            raise ValueError("ENABLE_CONTENT_DEBUG_LOGGING must not be True in production (Privacy Threat Model).")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        def get_bool(key: str, default: bool) -> bool:
            val = os.getenv(key)
            if val is None:
                return default
            return val.lower() in ("true", "1", "yes", "on")

        def get_int(key: str, default: int) -> int:
            val = os.getenv(key)
            if val is None:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        return cls(
            APP_ENV=os.getenv("APP_ENV", "development"),
            APP_BASE_URL=os.getenv("APP_BASE_URL", "http://localhost:7860"),
            SESSION_TTL_HOURS=get_int("SESSION_TTL_HOURS", 24),
            MAX_UPLOAD_BYTES=get_int("MAX_UPLOAD_BYTES", 52_428_800),
            MAX_SESSION_UPLOAD_BYTES=get_int("MAX_SESSION_UPLOAD_BYTES", 209_715_200),
            MAX_ZIP_ENTRIES=get_int("MAX_ZIP_ENTRIES", 5000),
            MAX_UNCOMPRESSED_BYTES=get_int("MAX_UNCOMPRESSED_BYTES", 524_288_000),
            MAX_COMPRESSION_RATIO=get_int("MAX_COMPRESSION_RATIO", 100),
            MAX_XML_PART_BYTES=get_int("MAX_XML_PART_BYTES", 104_857_600),
            BLACKBOX_API_KEY=os.getenv("BLACKBOX_API_KEY", ""),
            BLACKBOX_API_BASE=os.getenv("BLACKBOX_API_BASE", "https://api.blackbox.ai"),
            BLACKBOX_MODEL=os.getenv("BLACKBOX_MODEL", "blackboxai/deepseek/deepseek-v4-pro"),
            BLACKBOX_ZDR_REQUIRED=get_bool("BLACKBOX_ZDR_REQUIRED", True),
            CROSSREF_MAILTO=os.getenv("CROSSREF_MAILTO", ""),
            STORAGE_BACKEND=os.getenv("STORAGE_BACKEND", "local"),
            LOCAL_STORAGE_PATH=os.getenv("LOCAL_STORAGE_PATH", "/tmp/ai-docx-editor"),
            ENABLE_NATIVE_MENDELEY_LEGACY=get_bool("ENABLE_NATIVE_MENDELEY_LEGACY", False),
            ENABLE_NATIVE_MENDELEY_CITE=get_bool("ENABLE_NATIVE_MENDELEY_CITE", False),
            ENABLE_CONTENT_DEBUG_LOGGING=get_bool("ENABLE_CONTENT_DEBUG_LOGGING", False),
        )

    def load_capabilities(self, capabilities_file: Optional[Path] = None) -> Dict[str, Any]:
        """Loads and returns capability matrix dictionary."""
        if capabilities_file is None:
            # Look up default capabilities.example.yaml or capabilities.yaml
            root = Path(__file__).resolve().parent.parent.parent
            capabilities_file = root / "config" / "capabilities.yaml"
            if not capabilities_file.exists():
                capabilities_file = root / "config" / "capabilities.example.yaml"
        
        if not capabilities_file.exists():
            return {
                "models": {},
                "citation_adapters": {
                    "formatted_csl": {"enabled": True},
                    "placeholder_manifest": {"enabled": True},
                    "native_mendeley_legacy": {"enabled": self.ENABLE_NATIVE_MENDELEY_LEGACY},
                    "native_mendeley_cite": {"enabled": self.ENABLE_NATIVE_MENDELEY_CITE},
                },
                "mutations": {
                    "replace_text_span": True,
                    "insert_paragraph": True,
                    "replace_plain_paragraph": True,
                    "delete_plain_paragraph": True,
                }
            }
            
        with open(capabilities_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            # Override citation adapters from feature flags
            if "citation_adapters" in data:
                if "native_mendeley_legacy" in data["citation_adapters"]:
                    data["citation_adapters"]["native_mendeley_legacy"]["enabled"] = self.ENABLE_NATIVE_MENDELEY_LEGACY
                if "native_mendeley_cite" in data["citation_adapters"]:
                    data["citation_adapters"]["native_mendeley_cite"]["enabled"] = self.ENABLE_NATIVE_MENDELEY_CITE
            return data

# Global settings instance
settings = Settings.from_env()
