from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="steam_games", alias="MONGO_DB")
    mongo_collection: str = Field(default="games", alias="MONGO_COLLECTION")

    chroma_persist_dir: str = Field(default="./chroma_data", alias="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field(default="steam_games", alias="CHROMA_COLLECTION")

    steam_app_list_url: str = Field(
        default="https://store.steampowered.com/api/storesearch/",
        alias="STEAM_APP_LIST_URL",
    )
    steam_app_details_url: str = Field(
        default="https://store.steampowered.com/api/appdetails",
        alias="STEAM_APP_DETAILS_URL",
    )


settings = Settings()
