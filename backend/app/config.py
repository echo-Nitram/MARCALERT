from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://marcalert:marcalert@localhost:5432/marcalert"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Anthropic / Claude
    anthropic_api_key: str = ""

    # Resend (email)
    resend_api_key: str = ""
    email_from: str = "alertas@marcalert.uy"

    # Telegram (optional)
    telegram_bot_token: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Price IDs de Stripe (reemplazar con IDs reales del dashboard)
    stripe_price_starter: str = ""   # USD 29/mes — hasta 10 marcas
    stripe_price_pro: str = ""       # USD 79/mes — hasta 50 marcas
    stripe_price_estudio: str = ""   # USD 199/mes — ilimitadas + borradores

    # URLs del frontend (para redirects de Stripe)
    frontend_url: str = "http://localhost:5173"

    # DNPI / boletines
    dnpi_base_url: str = (
        "https://www.gub.uy/ministerio-industria-energia-mineria"
    )
    boletin_pdf_url_template: str = (
        "{base}/sites/{ministry}/files/documentos/publicaciones/Boletin%20{n}.pdf"
    )
    boletin_index_url_template: str = (
        "{base}/comunicacion/publicaciones/boletin-propiedad-industrial-ano-{year}"
    )
    boletin_pdf_ministry: str = (
        "ministerio-industria-energia-mineria"
    )

    # Ingestion
    logo_min_area_pt2: float = 50.0  # filter out vector noise (< this area in pt²)
    logo_proximity_max_gap_pt: float = 200.0  # max vertical gap between (210) and logo

    # Opposition deadline (días hábiles desde publicación del boletín)
    # NOTA: validar contra Ley 17.011 antes de usar como dato legal
    oposicion_dias_habiles: int = 30

    # Admin notifications
    admin_email: str = "admin@marcalert.uy"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
