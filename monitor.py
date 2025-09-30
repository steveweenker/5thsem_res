import asyncio
import os
import time
import aiohttp
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables from Railway/locally
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = os.getenv("URL")

# Settings
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 2))       # 2 Seconds
SCHEDULED_INTERVAL = int(os.getenv("SCHEDULED_INTERVAL", 7200))  # 2 hours
CONTINUOUS_DURATION = int(os.getenv("CONTINUOUS_DURATION", 900)) # 15 minutes

# Hardcoded result URLs (can also move to env if needed)
RESULT_URLS = [
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22156148040",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22156148042",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22156148051",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22156148018",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22156148012",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22104148015",
    "https://results.beup.ac.in/ResultsBTech5thSem2024_B2022Pub.aspx?Sem=V&RegNo=22101148008"
]


class Monitor:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.last_status = None
        self.last_scheduled = 0
        self.continuous_until = 0
        self.results_downloaded = False

    async def send_message(self, text):
        try:
            await self.bot.send_message(chat_id=CHAT_ID, text=text)
            await asyncio.sleep(1)
        except Exception:
            pass

    async def download_results(self):
        """Download all result pages simultaneously"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_single_result(session, url) for url in RESULT_URLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for r in results if r)
            await self.send_message(f"📥 Downloaded {success_count}/{len(RESULT_URLS)} results")
            return success_count > 0

    async def download_single_result(self, session, url):
        """Download single result page"""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html_content = await response.text()
                    reg_no = url.split('=')[-1]
                    await self.send_document(html_content, f"result_{reg_no}.html")
                    return True
        except Exception:
            return False
        return False

    async def send_document(self, content, filename):
        """Send HTML as document"""
        try:
            from io import BytesIO
            bio = BytesIO(content.encode('utf-8'))
            bio.seek(0)
            await self.bot.send_document(
                chat_id=CHAT_ID,
                document=bio,
                filename=filename
            )
            return True
        except Exception:
            return False

    async def check_site(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL, timeout=10) as response:
                    return "UP" if response.status == 200 else "DOWN"
        except:
            return "DOWN"

    async def monitor(self):
        await self.send_message("🔍 Monitoring started")

        while True:
            current_status = await self.check_site()
            current_time = time.time()
            status_changed = current_status != self.last_status

            # Immediate notification for status change
            if status_changed:
                if current_status == "UP":
                    self.continuous_until = current_time + CONTINUOUS_DURATION
                    self.results_downloaded = False
                    await self.send_message("🎉 Website is LIVE! (15min continuous updates + downloading results)")

                    asyncio.create_task(self.download_results())
                else:
                    await self.send_message("🔴 Website is DOWN")
                    self.results_downloaded = False

            # Continuous mode updates
            elif current_status == "UP" and current_time < self.continuous_until:
                time_left = int(self.continuous_until - current_time)
                await self.send_message(f"✅ Still live ({time_left}s left)")

                if not self.results_downloaded and time_left > 60:
                    self.results_downloaded = True
                    asyncio.create_task(self.download_results())

            # Scheduled updates
            elif current_time - self.last_scheduled >= SCHEDULED_INTERVAL and current_time >= self.continuous_until:
                status_text = "✅ Live" if current_status == "UP" else "🔴 Down"
                await self.send_message(f"📅 Scheduled: {status_text}")
                self.last_scheduled = current_time

            self.last_status = current_status
            await asyncio.sleep(CHECK_INTERVAL)


async def main():
    monitor = Monitor()
    await monitor.monitor()


if __name__ == '__main__':
    asyncio.run(main())
