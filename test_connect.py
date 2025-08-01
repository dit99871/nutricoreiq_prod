import asyncio
import ssl


async def test_smtp_connection():
    try:
        # Создание SSL-контекста
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Попытка подключения
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host="smtp.timeweb.ru",
                port=465,
                ssl=context,
            ),
            timeout=10,
        )
        print("Successfully connected to smtp.timeweb.ru:465")
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Failed to connect to smtp.timeweb.ru:465: {str(e)}")


asyncio.run(test_smtp_connection())
