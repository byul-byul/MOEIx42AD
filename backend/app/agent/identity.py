# /backend/app/agent/identity.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models import ChannelType, Customer, User

logger = get_logger(__name__)


async def resolve_user(
    db: AsyncSession,
    session_id: str,
    channel: ChannelType,
    phone: str | None,
    language: str,
) -> User:
    """Find-or-create the User for this session, and link it to a phone-based
    Customer when a phone number is known.

    `channel_user_id` is the part of `session_id` after the first underscore
    (e.g. "telegram_12345" -> "12345"), matching the convention already used
    by `tools.py::create_ticket`. For WhatsApp, `phone` is the channel
    address itself, so it is always known.
    """
    parts = session_id.split("_", 1)
    channel_user_id = parts[1] if len(parts) == 2 else session_id

    result = await db.execute(
        select(User).where(
            User.channel_user_id == channel_user_id,
            User.channel == channel,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(channel_user_id=channel_user_id, channel=channel, language=language)
        db.add(user)
        await db.flush()
        logger.info("Created user #%d | channel=%s | channel_user_id=%s", user.id, channel.value, channel_user_id)

    if phone and not user.customer_id:
        result = await db.execute(select(Customer).where(Customer.phone == phone))
        customer = result.scalar_one_or_none()
        if not customer:
            customer = Customer(phone=phone, language=language)
            db.add(customer)
            await db.flush()
            logger.info("Created customer #%d | phone=%s", customer.id, phone)
        user.customer_id = customer.id

    return user
