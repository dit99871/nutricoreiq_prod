# Анализ src/app/core/services/email.py

## Проблемы безопасности

### 1. Отсутствие валидации email адресов
```python
# ПРОБЛЕМА: Нет проверки валидности email перед отправкой
async def send_email(recipient: str, ...):
    # Нет валидации recipient

# ИСПРАВЛЕНИЕ: Добавить валидацию
import re
from email.utils import parseaddr

def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    if not email or len(email) > 254:
        return False

    # Проверка формата
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False

    # Проверка парсинга
    parsed = parseaddr(email)
    return '@' in parsed[1] and '.' in parsed[1].split('@')[1]

async def send_email(recipient: str, sender: str, subject: str, template: str, context: dict) -> None:
    """Отправка email с валидацией"""

    # Валидация получателя
    if not validate_email(recipient):
        log.error("Invalid recipient email: %s", recipient)
        raise ValueError(f"Invalid recipient email: {recipient}")

    # Валидация отправителя
    if not validate_email(sender):
        log.error("Invalid sender email: %s", sender)
        raise ValueError(f"Invalid sender email: {sender}")
```

### 2. Отсутствие rate limiting
```python
# ПРОБЛЕМА: Нет ограничения на отправку email
# ДОБАВИТЬ: Rate limiting для предотвращения спама

from datetime import datetime, timedelta
from collections import defaultdict

class EmailRateLimiter:
    def __init__(self):
        self._send_history = defaultdict(list)
        self._max_emails_per_hour = 10
        self._max_emails_per_day = 50

    def can_send_email(self, recipient: str) -> tuple[bool, str]:
        """Проверка возможности отправки email"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Очистка старых записей
        self._send_history[recipient] = [
            timestamp for timestamp in self._send_history[recipient]
            if timestamp > day_ago
        ]

        recent_emails = [
            timestamp for timestamp in self._send_history[recipient]
            if timestamp > hour_ago
        ]

        # Проверка лимитов
        if len(recent_emails) >= self._max_emails_per_hour:
            return False, "Превышен лимит отправки email в час"

        if len(self._send_history[recipient]) >= self._max_emails_per_day:
            return False, "Превышен лимит отправки email в день"

        return True, ""

    def record_email_sent(self, recipient: str):
        """Запись отправленного email"""
        self._send_history[recipient].append(datetime.now())

# Глобальный экземпляр
email_rate_limiter = EmailRateLimiter()
```

### 3. Отсутствие защиты от email injection
```python
# ПРОБЛЕМА: Возможность injection через subject или другие поля
def sanitize_email_content(content: str) -> str:
    """Очистка содержимого email от опасных символов"""
    # Удаление символов, которые могут использоваться для injection
    dangerous_chars = ['\r', '\n', '\0', '%0A', '%0D']

    for char in dangerous_chars:
        content = content.replace(char, '')

    return content.strip()

async def send_email(recipient: str, sender: str, subject: str, template: str, context: dict) -> None:
    """Отправка email с защитой от injection"""

    # Очистка входных данных
    recipient = sanitize_email_content(recipient)
    sender = sanitize_email_content(sender)
    subject = sanitize_email_content(subject)

    # Валидация после очистки
    if not validate_email(recipient) or not validate_email(sender):
        raise ValueError("Invalid email addresses after sanitization")
```

## Проблемы надежности

### 1. Неполная обработка ошибок
```python
# ПРОБЛЕМА: Ловится только SMTPException
except SMTPException as e:
    log.error("Error sending email to %s: %s", recipient, str(e))
    raise Exception(f"Failed to send email to {recipient}: {str(e)}")

# УЛУЧШЕНИЕ: Обработка всех возможных ошибок
import asyncio
from aiosmtplib.errors import SMTPAuthenticationError, SMTPConnectError, SMTPTimeoutError

async def send_email_with_retry(
    recipient: str,
    sender: str,
    subject: str,
    template: str,
    context: dict,
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """Отправка email с повторными попытками"""

    for attempt in range(max_retries):
        try:
            await _send_email_internal(recipient, sender, subject, template, context)
            log.info("Email sent successfully to: %s (attempt %d)", recipient, attempt + 1)
            return

        except SMTPAuthenticationError as e:
            log.error("SMTP authentication failed: %s", str(e))
            raise  # Не повторяем при ошибке аутентификации

        except SMTPConnectError as e:
            log.warning("SMTP connection failed (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
            if attempt == max_retries - 1:
                raise Exception(f"Failed to connect to SMTP server after {max_retries} attempts")

        except SMTPTimeoutError as e:
            log.warning("SMTP timeout (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
            if attempt == max_retries - 1:
                raise Exception(f"SMTP timeout after {max_retries} attempts")

        except Exception as e:
            log.error("Unexpected error sending email (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
            if attempt == max_retries - 1:
                raise

        # Ожидание перед повторной попыткой
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))  # Экспоненциальная задержка
```

### 2. Отсутствие template validation
```python
# ПРОБЛЕМА: Нет проверки существования шаблона
template_obj = env.get_template(template)

# УЛУЧШЕНИЕ: Валидация шаблона
def validate_template(template_name: str) -> bool:
    """Проверка существования шаблона"""
    try:
        env.get_template(template_name)
        return True
    except Exception:
        return False

async def send_email(...):
    # Проверка шаблона
    if not validate_template(template):
        log.error("Template not found: %s", template)
        raise ValueError(f"Email template not found: {template}")
```

### 3. Отсутствие мониторинга
```python
# ДОБАВИТЬ: Метрики отправки email
from prometheus_client import Counter, Histogram

email_sent_counter = Counter('emails_sent_total', 'Total emails sent', ['status', 'template'])
email_send_duration = Histogram('email_send_duration_seconds', 'Time spent sending emails')

async def send_email_with_metrics(...):
    """Отправка email с метриками"""
    start_time = time.time()

    try:
        await send_email_with_retry(...)
        email_sent_counter.labels(status='success', template=template).inc()

    except Exception as e:
        email_sent_counter.labels(status='failed', template=template).inc()
        raise
    finally:
        duration = time.time() - start_time
        email_send_duration.observe(duration)
```

## Отсутствующая функциональность

### 1. Поддержка разных типов email
```python
# ДОБАВИТЬ: Разные типы уведомлений
from enum import Enum

class EmailType(Enum):
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    NOTIFICATION = "notification"
    MARKETING = "marketing"

class EmailService:
    def __init__(self):
        self.rate_limiter = EmailRateLimiter()

    async def send_welcome_email(self, user) -> None:
        """Отправка приветственного письма"""
        await self._send_templated_email(
            recipient=user.email,
            email_type=EmailType.WELCOME,
            template="emails/welcome_email.html",
            context={
                "username": user.username,
                "button_link": settings.mail.button_link,
                "unsubscribe_link": f"{settings.mail.unsubscribe_link}?token={user.uid}",
            }
        )

    async def send_password_reset_email(self, user, reset_token: str) -> None:
        """Отправка письма сброса пароля"""
        await self._send_templated_email(
            recipient=user.email,
            email_type=EmailType.PASSWORD_RESET,
            template="emails/password_reset.html",
            context={
                "username": user.username,
                "reset_link": f"{settings.mail.button_link}/reset-password?token={reset_token}",
                "expiry_hours": 24,
            }
        )

    async def send_verification_email(self, user, verification_token: str) -> None:
        """Отправка письма подтверждения email"""
        await self._send_templated_email(
            recipient=user.email,
            email_type=EmailType.EMAIL_VERIFICATION,
            template="emails/email_verification.html",
            context={
                "username": user.username,
                "verification_link": f"{settings.mail.button_link}/verify-email?token={verification_token}",
            }
        )
```

### 2. Unsubscribe механизм
```python
# ДОБАВИТЬ: Обработка отписок
async def handle_unsubscribe(unsubscribe_token: str, session: AsyncSession) -> bool:
    """Обработка отписки от рассылки"""
    try:
        # Декодировать токен и найти пользователя
        user_uid = decode_unsubscribe_token(unsubscribe_token)

        # Обновить статус подписки
        await update_subscription_status(session, user_uid, False)

        log.info("User %s unsubscribed successfully", user_uid)
        return True

    except Exception as e:
        log.error("Error processing unsubscribe: %s", str(e))
        return False

def generate_unsubscribe_token(user_uid: str) -> str:
    """Генерация токена для отписки"""
    payload = {
        "user_uid": user_uid,
        "action": "unsubscribe",
        "exp": datetime.now(dt.UTC) + timedelta(days=365)  # Длительный срок
    }
    return encode_jwt(payload)
```

## Полное исправленное решение

```python
# src/app/core/services/email.py - улучшенная версия
import asyncio
import re
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr
from enum import Enum
from typing import Dict, List, Optional

import aiosmtplib
from aiosmtplib.errors import (
    SMTPException, SMTPAuthenticationError,
    SMTPConnectError, SMTPTimeoutError
)
from jinja2 import Environment, FileSystemLoader
from prometheus_client import Counter, Histogram

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("email_service")

# Метрики
email_sent_counter = Counter('emails_sent_total', 'Total emails sent', ['status', 'template'])
email_send_duration = Histogram('email_send_duration_seconds', 'Time spent sending emails')

# Настройка Jinja2
env = Environment(loader=FileSystemLoader("src/app/templates"))


class EmailType(Enum):
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    NOTIFICATION = "notification"


class EmailRateLimiter:
    """Rate limiter для отправки email"""

    def __init__(self):
        self._send_history: Dict[str, List[datetime]] = {}
        self._max_emails_per_hour = 10
        self._max_emails_per_day = 50

    def can_send_email(self, recipient: str) -> tuple[bool, str]:
        """Проверка возможности отправки email"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Инициализация истории для нового получателя
        if recipient not in self._send_history:
            self._send_history[recipient] = []

        # Очистка старых записей
        self._send_history[recipient] = [
            timestamp for timestamp in self._send_history[recipient]
            if timestamp > day_ago
        ]

        recent_emails = [
            timestamp for timestamp in self._send_history[recipient]
            if timestamp > hour_ago
        ]

        # Проверка лимитов
        if len(recent_emails) >= self._max_emails_per_hour:
            return False, "Превышен лимит отправки email в час"

        if len(self._send_history[recipient]) >= self._max_emails_per_day:
            return False, "Превышен лимит отправки email в день"

        return True, ""

    def record_email_sent(self, recipient: str):
        """Запись отправленного email"""
        if recipient not in self._send_history:
            self._send_history[recipient] = []
        self._send_history[recipient].append(datetime.now())


class EmailService:
    """Сервис для отправки email с улучшенной безопасностью и надежностью"""

    def __init__(self):
        self.rate_limiter = EmailRateLimiter()

    def validate_email(self, email: str) -> bool:
        """Валидация email адреса"""
        if not email or len(email) > 254:
            return False

        # Проверка формата
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False

        # Проверка парсинга
        parsed = parseaddr(email)
        return '@' in parsed[1] and '.' in parsed[1].split('@')[1]

    def sanitize_email_content(self, content: str) -> str:
        """Очистка содержимого email от опасных символов"""
        dangerous_chars = ['\r', '\n', '\0', '%0A', '%0D']

        for char in dangerous_chars:
            content = content.replace(char, '')

        return content.strip()

    def validate_template(self, template_name: str) -> bool:
        """Проверка существования шаблона"""
        try:
            env.get_template(template_name)
            return True
        except Exception:
            return False

    async def send_email(
        self,
        recipient: str,
        sender: str,
        subject: str,
        template: str,
        context: dict,
        email_type: EmailType = EmailType.NOTIFICATION,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> None:
        """Безопасная отправка email с повторными попытками"""

        start_time = time.time()

        try:
            # Очистка входных данных
            recipient = self.sanitize_email_content(recipient)
            sender = self.sanitize_email_content(sender)
            subject = self.sanitize_email_content(subject)

            # Валидация
            if not self.validate_email(recipient):
                raise ValueError(f"Invalid recipient email: {recipient}")
            if not self.validate_email(sender):
                raise ValueError(f"Invalid sender email: {sender}")
            if not self.validate_template(template):
                raise ValueError(f"Email template not found: {template}")

            # Проверка rate limiting
            can_send, reason = self.rate_limiter.can_send_email(recipient)
            if not can_send:
                log.warning("Rate limit exceeded for %s: %s", recipient, reason)
                raise Exception(f"Rate limit exceeded: {reason}")

            # Отправка с повторными попытками
            await self._send_email_with_retry(
                recipient, sender, subject, template, context,
                max_retries, retry_delay
            )

            # Запись успешной отправки
            self.rate_limiter.record_email_sent(recipient)
            email_sent_counter.labels(status='success', template=template).inc()

            log.info("Email sent successfully to: %s", recipient)

        except Exception as e:
            email_sent_counter.labels(status='failed', template=template).inc()
            log.error("Failed to send email to %s: %s", recipient, str(e))
            raise
        finally:
            duration = time.time() - start_time
            email_send_duration.observe(duration)

    async def _send_email_with_retry(
        self,
        recipient: str,
        sender: str,
        subject: str,
        template: str,
        context: dict,
        max_retries: int,
        retry_delay: int
    ) -> None:
        """Внутренний метод отправки с повторными попытками"""

        for attempt in range(max_retries):
            try:
                await self._send_email_internal(recipient, sender, subject, template, context)
                return

            except SMTPAuthenticationError as e:
                log.error("SMTP authentication failed: %s", str(e))
                raise  # Не повторяем при ошибке аутентификации

            except SMTPConnectError as e:
                log.warning("SMTP connection failed (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to connect to SMTP server after {max_retries} attempts")

            except SMTPTimeoutError as e:
                log.warning("SMTP timeout (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
                if attempt == max_retries - 1:
                    raise Exception(f"SMTP timeout after {max_retries} attempts")

            except Exception as e:
                log.error("Unexpected error sending email (attempt %d/%d): %s", attempt + 1, max_retries, str(e))
                if attempt == max_retries - 1:
                    raise

            # Экспоненциальная задержка
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

    async def _send_email_internal(
        self,
        recipient: str,
        sender: str,
        subject: str,
        template: str,
        context: dict
    ) -> None:
        """Внутренний метод отправки email"""

        # Рендеринг шаблона
        template_obj = env.get_template(template)
        html_content = template_obj.render(**context)

        # Создание сообщения
        message = MIMEMultipart("alternative")
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject

        # Добавление HTML части
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Отправка
        await aiosmtplib.send(
            message,
            recipients=[recipient],
            sender=sender,
            hostname=settings.mail.host,
            port=settings.mail.port,
            username=settings.mail.username,
            password=settings.mail.password,
            use_tls=settings.mail.use_tls,
            timeout=60,
        )

    # Специализированные методы
    async def send_welcome_email(self, user) -> None:
        """Отправка приветственного письма"""
        await self.send_email(
            recipient=str(user.email),
            sender=settings.mail.username,
            subject="Добро пожаловать в NutriCoreIQ!",
            template="emails/welcome_email.html",
            context={
                "username": user.username,
                "button_link": settings.mail.button_link,
                "unsubscribe_link": f"{settings.mail.unsubscribe_link}?token={user.uid}",
            },
            email_type=EmailType.WELCOME
        )


# Глобальный экземпляр сервиса
email_service = EmailService()

# Функции для обратной совместимости
async def send_email(recipient: str, sender: str, subject: str, template: str, context: dict) -> None:
    """Функция обратной совместимости"""
    await email_service.send_email(recipient, sender, subject, template, context)

async def send_welcome_email(user) -> None:
    """Функция обратной совместимости"""
    await email_service.send_welcome_email(user)
```

## Приоритет исправлений

1. **Критический**: Добавить валидацию email адресов
2. **Высокий**: Добавить rate limiting и защиту от спама
3. **Высокий**: Улучшить обработку ошибок с retry логикой
4. **Средний**: Добавить метрики и мониторинг
5. **Низкий**: Добавить специализированные типы email
