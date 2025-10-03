# mailing/utils.py
from datetime import datetime, timedelta
from .models import MailingConfig

class PaymentChecker:
    def __init__(self, db):
        self.db = db
    
    def get_new_annual_payments(self):
        """Получает новые платежи за годовые тарифы для отправки инструкций"""
        cursor = self.db.cursor()
        
        # Вычисляем дату, начиная с которой проверяем платежи
        cutoff_date = datetime.now() - timedelta(days=MailingConfig.MAX_PAYMENT_AGE_DAYS)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        query = '''
        SELECT p.id, p.user_id, p.tariff_name, p.updated_at, t.username
        FROM payments p
        LEFT JOIN tutors t ON p.user_id = t.telegram_id
        LEFT JOIN instruction_mailing im ON p.id = im.payment_id
        WHERE p.status = 'succeeded'
        AND p.tariff_name IN ({})
        AND p.updated_at >= ?
        AND im.id IS NULL  -- Инструкция еще не отправлялась
        ORDER BY p.updated_at DESC
        '''.format(','.join(['?'] * len(MailingConfig.TARGET_TARIFFS)))
        
        params = MailingConfig.TARGET_TARIFFS + [cutoff_date_str]
        
        return cursor.execute(query, params).fetchall()
    
    def is_recent_payment(self, updated_at: str) -> bool:
        """Проверяет, является ли платеж недавним"""
        payment_date = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
        cutoff_date = datetime.now() - timedelta(days=MailingConfig.MAX_PAYMENT_AGE_DAYS)
        return payment_date >= cutoff_date
