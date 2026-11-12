import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from playwright.async_api import async_playwright

TOKEN = os.getenv("TOKEN", "ТВОЙ_ТОКЕН")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "https://tvoj-servis.onrender.com")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_dtek_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 1024})
        
        try:
            await page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            screenshot_path = "schedule.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            return screenshot_path
        except Exception as e:
            print(f"Ошибка при создании скриншота: {e}")
            return None
        finally:
            await browser.close()

@dp.message(Command("start", "check"))
async def cmd_check(message: types.Message):
    await message.answer("🔍 Запускаю облачный браузер, получаю актуальный график ДТЭК...")
    
    photo_path = await get_dtek_screenshot()
    
    if photo_path and os.path.exists(photo_path):
        photo = types.FSInputFile(photo_path)
        await message.answer_photo(photo, caption="📊 Актуальный график отключений")
    else:
        await message.answer("❌ Не удалось получить скриншот графика. Попробуйте позже.")

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

def main():
    dp.startup.register(on_startup)
    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
  
