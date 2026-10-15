#!/usr/bin/env python3
import os
import asyncio
import httpx
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

CLIENT_ID = os.getenv("HH_CLIENT_ID")
CLIENT_SECRET = os.getenv("HH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("HH_REDIRECT_URI")

def get_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "negotiations"
    }
    return f"https://hh.ru/oauth/authorize?{urlencode(params)}"

async def exchange_code(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://hh.ru/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            }
        )
        response.raise_for_status()
        return response.json()

async def main():
    print("=" * 60)
    print("HeadHunter OAuth Authorization")
    print("=" * 60)
    print("\n1. Откройте эту ссылку в браузере:\n")
    print(get_auth_url())
    print("\n2. Авторизуйтесь и разрешите доступ")
    print("3. Скопируйте код из URL (после ?code=)\n")

    code = input("Введите код авторизации: ").strip()

    print("\nОбмен кода на токены...")
    tokens = await exchange_code(code)

    print("\n✅ Успешно получены токены!")
    print(f"Access Token: {tokens['access_token'][:50]}...")
    print(f"Refresh Token: {tokens['refresh_token'][:50]}...")
    print(f"Expires in: {tokens['expires_in']} seconds")

    print("\n📝 Сохраните эти токены в .env файл:")
    print(f"\nHH_ACCESS_TOKEN={tokens['access_token']}")
    print(f"HH_REFRESH_TOKEN={tokens['refresh_token']}")

    with open('.env', 'a') as f:
        f.write(f"\n\n# OAuth tokens (expires at {tokens['expires_in']} seconds)\n")
        f.write(f"HH_ACCESS_TOKEN={tokens['access_token']}\n")
        f.write(f"HH_REFRESH_TOKEN={tokens['refresh_token']}\n")

    print("\n✅ Токены сохранены в .env файл")

if __name__ == "__main__":
    asyncio.run(main())
