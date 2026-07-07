from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="steam_games", alias="MONGO_DB")
    mongo_collection: str = Field(default="games", alias="MONGO_COLLECTION")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=300, alias="CACHE_TTL_SECONDS")

    chroma_persist_dir: str = Field(default="./chroma_data", alias="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field(default="steam_games", alias="CHROMA_COLLECTION")

    rustfs_endpoint: str = Field(default="http://localhost:9000", alias="RUSTFS_ENDPOINT")
    rustfs_access_key: str = Field(default="", alias="RUSTFS_ACCESS_KEY")
    rustfs_secret_key: str = Field(default="", alias="RUSTFS_SECRET_KEY")
    rustfs_region: str = Field(default="us-east-1", alias="RUSTFS_REGION")
    rustfs_secure: bool = Field(default=False, alias="RUSTFS_SECURE")
    rustfs_gameplay_bucket: str = Field(default="gameplay-videos", alias="RUSTFS_GAMEPLAY_BUCKET")
    rustfs_catalog_bucket: str = Field(default="catalog-media", alias="RUSTFS_CATALOG_BUCKET")

    steam_app_list_url: str = Field(
        default="https://store.steampowered.com/api/storesearch/",
        alias="STEAM_APP_LIST_URL",
    )
    steam_app_details_url: str = Field(
        default="https://store.steampowered.com/api/appdetails",
        alias="STEAM_APP_DETAILS_URL",
    )


settings = Settings()
