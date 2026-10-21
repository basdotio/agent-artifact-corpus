from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(primary_key=True)
    owner_id: Mapped[str]
    amount_cents: Mapped[int]
    status: Mapped[str] = mapped_column(default="open")
