import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from playwright.async_api import async_playwright

TOKEN = os.getenv("TOKEN", "8666917034:AAG5Xm8YvNZW9P187qNm62amdBrmplIrJgs")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://dtek-bot.onrender.com")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для сохранения адресов
class BotStates(StatesGroup):
    waiting_for_address = State()

# Хранилище адресов пользователей в памяти (для примера)
user_addresses = {}

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📍 Добавить адрес")
    builder.button(text="📊 Проверить график")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

async def get_dtek_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 1024})
        
        try:
            await page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Закрываем всплывающее окно (нажимаем на крестик, если он есть)
            try:
                # Ищем крестик по селектору или тексту
                close_btn = page.locator("button.close, .popup-close, svg, [aria-label='Close']").first
                if await close_btn.isVisible(timeout=3000):
                    await close_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception:
                # Если крестик не нашелся, пробуем кликнуть в пустую область или просто идем дальше
                pass

            screenshot_path = "schedule.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            return screenshot_path
        except Exception as e:
            print(f"Ошибка при создании скриншота: {e}")
            return None
        finally:
            await browser.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для отслеживания графиков ДТЭК в Днепре.\n"
        "Вы можете сохранить свои адреса и получать актуальные скриншоты графиков.",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda msg: msg.text == "📍 Добавить адрес")
async def add_address_start(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите ваш адрес (например: ул. Сонячна, 1):")
    await state.set_state(BotStates.waiting_for_address)

@dp.message(BotStates.waiting_for_address)
async def save_address(message: types.Message, state: FSMContext):
    address = message.text
    user_id = message.from_user.id
    
    if user_id not in user_addresses:
        user_addresses[user_id] = []
    user_addresses[user_id].append(address)
    
    await state.clear()
    await message.answer(
        f"✅ Адрес «{address}» успешно сохранен!\nВсего адресов: {len(user_addresses[user_id])}",
        reply_markup=get_main_keyboard()
    )

@dp.message(lambda msg: msg.text == "📊 Проверить график" or msg.text == "/check")
async def cmd_check(message: types.Message):
    user_id = message.from_user.id
    saved = user_addresses.get(user_id, [])
    
    text = "🔍 Запускаю облачный браузер, закрываю всплывающее окно и получаю график ДТЭК..."
    if saved:
        text += f"\n📌 Ваши сохраненные адреса: {', '.join(saved)}"
        
    await message.answer(text)
    
    photo_path = await get_dtek_screenshot()
    
    if photo_path and os.path.exists(
    
