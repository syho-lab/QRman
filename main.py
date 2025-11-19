import os
import logging
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
import qrcode
from io import BytesIO
from fastapi import FastAPI, Request
import uvicorn
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
def get_base_url():
    base_url = os.getenv("BASE_URL")
    if base_url:
        return base_url.rstrip('/')
    
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        return render_url.rstrip('/')
    
    # Для Render автоматически определяем URL
    render_service = os.getenv("RENDER_SERVICE_NAME")
    if render_service:
        return f"https://{render_service}.onrender.com"
    
    return "https://your-app.onrender.com"  # fallback

BASE_URL = get_base_url()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set!")
    raise ValueError("BOT_TOKEN is required")

logger.info(f"Bot configured with BASE_URL: {BASE_URL}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
app = FastAPI(title="QR Master Bot")

# Добавляем сжатие GZIP
app.add_middleware(GZipMiddleware, minimum_size=500)

# Подключаем роутер
dp.include_router(router)

# Красивые эмодзи и стили
class BotStyles:
    WELCOME_TEXT = """
🎉 <b>Добро пожаловать в QR Master Bot!</b>

✨ <i>Многофункциональный бот для работы с QR-кодами</i>

🛠 <b>Что умеет этот бот:</b>
• 📷 <b>Сканировать</b> QR-коды через камеру
• 🔄 <b>Генерировать</b> QR-коды из текста и ссылок
• 💾 <b>Создавать</b> красивые QR-коды в разных стилях
• ⚡ <b>Быстро работать</b> и просто использовать

👇 <b>Выберите действие:</b>
    """
    
    QR_GENERATED = """
✅ <b>QR-код успешно создан!</b>

📊 <b>Информация:</b>
• 📏 Размер: 300x300 пикселей
• 🎨 Версия: QR Code v7
• 💾 Коррекция ошибок: 30%

💡 <i>Сохраните изображение или поделитесь им!</i>
    """
    
    ERROR_TEXT = """
❌ <b>Произошла ошибка!</b>

⚠️ <i>Пожалуйста, попробуйте еще раз или обратитесь в поддержку.</i>
    """

# Главное меню с инлайн-кнопками
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📷 Сканировать QR-код", 
        web_app=WebAppInfo(url=f"{BASE_URL}/scanner")
    )
    builder.button(
        text="🔄 Сгенерировать QR-код",
        web_app=WebAppInfo(url=f"{BASE_URL}/generator")
    )
    builder.button(
        text="🚀 Быстрая генерация",
        callback_data="quick_generate"
    )
    builder.adjust(2, 1)
    return builder.as_markup()

# Генерация QR-кода
def generate_qr_code(data: str) -> BytesIO:
    """Генерирует QR-код и возвращает BytesIO объект"""
    qr = qrcode.QRCode(
        version=7,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

# Команда /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        BotStyles.WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# Быстрая генерация QR-кода
@router.callback_query(F.data == "quick_generate")
async def quick_generate_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "🚀 <b>Быстрая генерация QR-кода</b>\n\n"
        "📝 <i>Отправьте мне текст или ссылку, и я создам QR-код!</i>\n\n"
        "💡 <b>Примеры:</b>\n"
        "• https://example.com\n"
        "• Ваш текст здесь\n"
        "• +79991234567\n"
        "• YOUR_WIFI_NAME;WPA;PASSWORD",
        parse_mode="HTML"
    )
    await callback.answer()

# Обработка текста для генерации QR-кода
@router.message(F.text)
async def generate_qr_from_text(message: types.Message):
    text = message.text
    
    # Проверяем, не является ли текст командой
    if text.startswith('/'):
        return
    
    try:
        await message.answer("⏳ <i>Создаю QR-код...</i>", parse_mode="HTML")
        
        # Генерируем QR-код
        qr_image = generate_qr_code(text)
        
        # Отправляем изображение
        await message.answer_photo(
            types.BufferedInputFile(
                qr_image.getvalue(),
                filename="qrcode.png"
            ),
            caption=BotStyles.QR_GENERATED,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error generating QR: {e}")
        await message.answer(BotStyles.ERROR_TEXT, parse_mode="HTML")

# Обработка данных из WebApp
@router.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        qr_data = message.web_app_data.data
        await message.answer(
            f"✅ <b>Результат сканирования:</b>\n\n"
            f"<code>{qr_data}</code>\n\n"
            f"💡 <i>Отправьте этот текст мне, чтобы создать QR-код!</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"WebApp error: {e}")
        await message.answer(BotStyles.ERROR_TEXT, parse_mode="HTML")

# Создаем директорию для статических файлов
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware для кэширования
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(('.html', '.css', '.js')):
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response

@app.get("/")
async def root():
    return {"status": "QR Bot is running!", "webhook_url": f"{BASE_URL}/webhook"}

@app.get("/scanner")
async def scanner_page():
    return FileResponse("static/scanner.html")

@app.get("/generator")
async def generator_page():
    return FileResponse("static/generator.html")

# Эндпоинт для проверки здоровья (для cron-job.org)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "QR Telegram Bot",
        "webhook_set": bool(BOT_TOKEN and BASE_URL)
    }

# Lifespan для управления вебхуком
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Устанавливаем вебхук только если все переменные настроены
        if BOT_TOKEN and BASE_URL:
            webhook_url = f"{BASE_URL}/webhook"
            logger.info(f"Setting webhook to: {webhook_url}")
            
            # Сначала удаляем старый вебхук
            await bot.delete_webhook(drop_pending_updates=True)
            
            # Устанавливаем новый вебхук
            await bot.set_webhook(webhook_url)
            logger.info("Webhook set successfully!")
        else:
            logger.error("Cannot set webhook: BOT_TOKEN or BASE_URL not configured")
            
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
    
    yield
    
    # При завершении работы
    try:
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error closing session: {e}")

app.router.lifespan_context = lifespan

# Вебхук для Telegram
@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        telegram_update = types.Update(**update)
        await dp.feed_update(bot=bot, update=telegram_update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
