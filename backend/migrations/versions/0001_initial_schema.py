"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- ENUM types ----------------------------------------------------------
    subscription_tier = postgresql.ENUM(
        "starter", "pro", "estudio", name="subscriptiontier", create_type=False
    )
    subscription_tier.create(op.get_bind(), checkfirst=True)

    sensibilidad_umbral = postgresql.ENUM(
        "bajo", "medio", "alto", name="sensibilidadumbral", create_type=False
    )
    sensibilidad_umbral.create(op.get_bind(), checkfirst=True)

    tipo_marca = postgresql.ENUM(
        "denominativa", "figurativa", "mixta", name="tipomarca", create_type=False
    )
    tipo_marca.create(op.get_bind(), checkfirst=True)

    estado_alerta = postgresql.ENUM(
        "nueva", "revisada", "en_oposicion", "descartada",
        name="estadoalerta", create_type=False
    )
    estado_alerta.create(op.get_bind(), checkfirst=True)

    # -- tenants -------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("starter", "pro", "estudio", name="subscriptiontier"),
            nullable=False,
            server_default="starter",
        ),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("subscription_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("draft_credits", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # -- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("notify_email", sa.Boolean(), nullable=True),
        sa.Column("notify_telegram", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # -- marcas_vigiladas ----------------------------------------------------
    op.create_table(
        "marcas_vigiladas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("denominacion", sa.String(500), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("denominativa", "figurativa", "mixta", name="tipomarca"),
            nullable=False,
            server_default="denominativa",
        ),
        sa.Column("clases_niza", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column(
            "sensibilidad",
            sa.Enum("bajo", "medio", "alto", name="sensibilidadumbral"),
            nullable=False,
            server_default="medio",
        ),
        sa.Column("cliente_nombre", sa.String(500), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activa", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marcas_vigiladas_tenant_id", "marcas_vigiladas", ["tenant_id"])

    # -- boletines -----------------------------------------------------------
    op.create_table(
        "boletines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("fecha_publicacion", sa.Date(), nullable=False),
        sa.Column("pdf_url", sa.String(500), nullable=False),
        sa.Column("pdf_size_bytes", sa.Integer(), nullable=True),
        sa.Column("paginas", sa.Integer(), nullable=True),
        sa.Column("total_solicitudes", sa.Integer(), nullable=True),
        sa.Column("procesado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("procesado_at", sa.DateTime(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero"),
    )
    op.create_index("ix_boletines_numero", "boletines", ["numero"])

    # -- solicitudes ---------------------------------------------------------
    op.create_table(
        "solicitudes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("boletin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("boletin_numero", sa.Integer(), nullable=False),
        sa.Column("expediente", sa.String(50), nullable=False),
        sa.Column("denominacion", sa.String(500), nullable=True),
        sa.Column("solicitante", sa.String(500), nullable=True),
        sa.Column("pais_solicitante", sa.String(10), nullable=True),
        sa.Column("fecha_presentacion", sa.Date(), nullable=True),
        sa.Column("clases_niza", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("agente_direccion", sa.Text(), nullable=True),
        sa.Column("colores_reivindicados", sa.String(500), nullable=True),
        sa.Column("pagina_boletin", sa.Integer(), nullable=True),
        sa.Column("logo_data", sa.LargeBinary(), nullable=True),
        sa.Column("logo_mime", sa.String(50), nullable=True),
        sa.Column("logo_width_pt", sa.Float(), nullable=True),
        sa.Column("logo_height_pt", sa.Float(), nullable=True),
        sa.Column("raw_block", sa.Text(), nullable=True),
        sa.Column("parsed_by_ai", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["boletin_id"], ["boletines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solicitudes_boletin_id", "solicitudes", ["boletin_id"])
    op.create_index("ix_solicitudes_boletin_numero", "solicitudes", ["boletin_numero"])
    op.create_index("ix_solicitudes_expediente", "solicitudes", ["expediente"])

    # -- alertas -------------------------------------------------------------
    op.create_table(
        "alertas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marca_vigilada_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solicitud_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_denominativo", sa.Float(), nullable=False),
        sa.Column("score_clase", sa.Float(), nullable=False),
        sa.Column("score_total", sa.Float(), nullable=False),
        sa.Column("score_figurativo", sa.Float(), nullable=True),
        sa.Column("detalle_fonetico", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explicacion_ia", sa.Text(), nullable=True),
        sa.Column("fecha_limite_oposicion", sa.Date(), nullable=True),
        sa.Column("dias_habiles_restantes", sa.Integer(), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("nueva", "revisada", "en_oposicion", "descartada", name="estadoalerta"),
            nullable=False,
            server_default="nueva",
        ),
        sa.Column("notificado_email", sa.Boolean(), nullable=True),
        sa.Column("notificado_telegram", sa.Boolean(), nullable=True),
        sa.Column("borrador_oposicion", sa.Text(), nullable=True),
        sa.Column("borrador_generado_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["marca_vigilada_id"], ["marcas_vigiladas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["solicitud_id"], ["solicitudes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alertas_tenant_id", "alertas", ["tenant_id"])
    op.create_index("ix_alertas_marca_vigilada_id", "alertas", ["marca_vigilada_id"])
    op.create_index("ix_alertas_solicitud_id", "alertas", ["solicitud_id"])

    # -- metricas_boletin ----------------------------------------------------
    op.create_table(
        "metricas_boletin",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("boletin_numero", sa.Integer(), nullable=False),
        sa.Column("total_solicitudes_analizadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_colisiones_detectadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_descartadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metricas_boletin_tenant_id", "metricas_boletin", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("metricas_boletin")
    op.drop_table("alertas")
    op.drop_table("solicitudes")
    op.drop_table("boletines")
    op.drop_table("marcas_vigiladas")
    op.drop_table("users")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS estadoalerta")
    op.execute("DROP TYPE IF EXISTS tipomarca")
    op.execute("DROP TYPE IF EXISTS sensibilidadumbral")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
