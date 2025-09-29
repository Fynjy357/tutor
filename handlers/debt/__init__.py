# handlers/debt/__init__.py
from .payment_debts import router as payment_debts_router

__all__ = ['payment_debts_router']
