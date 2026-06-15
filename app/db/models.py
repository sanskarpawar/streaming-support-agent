from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Pagila tables (subset used by tools) ────────────────────────────────────

class Film(Base):
    __tablename__ = "film"

    film_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    release_year = Column(Integer)
    rental_rate = Column(String(10))
    rating = Column(String(10))
    streaming_available = Column(Boolean, nullable=False, server_default="false")

    inventories = relationship("Inventory", back_populates="film")


class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False)


class FilmCategory(Base):
    __tablename__ = "film_category"

    film_id = Column(Integer, ForeignKey("film.film_id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("category.category_id"), primary_key=True)


class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True)
    first_name = Column(String(45), nullable=False)
    last_name = Column(String(45), nullable=False)
    email = Column(String(50))

    rentals = relationship("Rental", back_populates="customer")
    subscriptions = relationship("StreamingSubscription", back_populates="customer")


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey("film.film_id"), nullable=False)

    film = relationship("Film", back_populates="inventories")
    rentals = relationship("Rental", back_populates="inventory")


class Rental(Base):
    __tablename__ = "rental"

    rental_id = Column(Integer, primary_key=True)
    rental_date = Column(DateTime, nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.inventory_id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.customer_id"), nullable=False)
    return_date = Column(DateTime)

    customer = relationship("Customer", back_populates="rentals")
    inventory = relationship("Inventory", back_populates="rentals")


# ── Migration 002: streaming subscriptions ───────────────────────────────────

class StreamingSubscription(Base):
    __tablename__ = "streaming_subscription"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id"), nullable=False)
    plan_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    auto_renew = Column(Boolean, nullable=False, default=True)

    customer = relationship("Customer", back_populates="subscriptions")


# ── Migration 003: conversation session & history ────────────────────────────

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String(255), primary_key=True)
    customer_id = Column(Integer, nullable=False)
    title = Column(String(200))
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ConversationMessage", back_populates="session", order_by="ConversationMessage.created_at"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey("conversation_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent_used = Column(String(50))
    intent = Column(String(50))
    tools_used = Column(JSONB)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    session = relationship("ConversationSession", back_populates="messages")
