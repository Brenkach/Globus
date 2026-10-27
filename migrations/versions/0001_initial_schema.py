"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Вираз має збігатися з app/core/geo.py::geo_point, інакше індекс не використовуватиметься.
GEO_EXPR = "(ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography)"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        *_timestamps(),
    )

    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.true(), nullable=False),
        *_timestamps(),
    )
    op.execute(f"CREATE INDEX ix_restaurants_location ON restaurants USING gist ({GEO_EXPR})")

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("restaurant_id", sa.Integer, sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_menu_items_price_positive"),
        *_timestamps(),
    )
    op.create_index("ix_menu_items_restaurant_id", "menu_items", ["restaurant_id"])

    op.create_table(
        "couriers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum("OFFLINE", "AVAILABLE", "BUSY", name="courier_status"),
            server_default="OFFLINE",
            nullable=False,
        ),
        sa.Column("lat", sa.Float),
        sa.Column("lng", sa.Float),
        sa.Column("location_updated_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_couriers_status", "couriers", ["status"])
    op.execute(f"CREATE INDEX ix_couriers_location ON couriers USING gist ({GEO_EXPR})")

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("restaurant_id", sa.Integer, sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("courier_id", sa.Integer, sa.ForeignKey("couriers.id")),
        sa.Column(
            "status",
            sa.Enum(
                "CREATED", "ACCEPTED", "COOKING", "READY", "PICKED_UP", "DELIVERED", "CANCELLED",
                name="order_status",
            ),
            server_default="CREATED",
            nullable=False,
        ),
        sa.Column("delivery_address", sa.String(255), nullable=False),
        sa.Column("delivery_lat", sa.Float, nullable=False),
        sa.Column("delivery_lng", sa.Float, nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        *_timestamps(),
    )
    for col in ("customer_id", "restaurant_id", "courier_id", "status"):
        op.create_index(f"ix_orders_{col}", "orders", [col])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("menu_item_id", sa.Integer, sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    for table in ("order_items", "orders", "couriers", "menu_items", "restaurants", "customers"):
        op.drop_table(table)
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS courier_status")
