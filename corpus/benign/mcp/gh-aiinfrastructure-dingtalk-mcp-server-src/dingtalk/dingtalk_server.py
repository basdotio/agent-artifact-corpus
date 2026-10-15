import json as JSON
import logging
import os
import time
from dotenv import load_dotenv
from typing import Any, Optional
import aiohttp

class DingtalkServer:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self.logger = logging.getLogger(__name__)

        load_dotenv()
        self.app_key = os.getenv("DD_APP_KEY")
        self.app_secret = os.getenv("DD_APP_SECRET")
        self.access_token: Optional[str] = None
        self.token_expires = 0
        self.v2_access_token: Optional[str] = None
        self.v2_token_expires = 0
        self.session = None
        self.logger.info("DingtalkServer initialized.")

    async def ensure_session(self):
        if self.session is None:
            self.logger.info("Session created.")
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()
            self.logger.info("Session closed.")

    async def get_access_token(self):
        self.logger.debug("Getting access token.")

        if self.access_token and time.time() < self.token_expires:
            self.logger.debug("Access token is still valid.")
            return self.access_token
        
        await self.ensure_session()
        app_key = self.app_key
        app_secret = self.app_secret

        if not all([app_key, app_secret]):
            self.logger.error("App key and secret are required.")
            raise ValueError("App key and secret are required.")
        
        url = "https://oapi.dingtalk.com/gettoken"
        params = {
            "appkey": app_key,
            "appsecret": app_secret
        }

        async with self.session.get(url, params=params) as response:
            data = await response.json()
            logging.info(f"get access token response: {data}")
            if data.get("errcode") == 0:
                self.access_token = data.get("access_token")
                self.token_expires = time.time() + data["expires_in"] - 200
                return self.access_token
            else:
                self.logger.error(f"Failed to get access token: {data}")
                raise Exception("Failed to get access token")

    async def get_old(self, url:str, params:dict[str, Any] | None = None) -> str:
        access_token = await self.get_access_token()
        p = {"access_token": access_token}
        if params is not None:
            p.update(params)

        async with self.session.get(url, params=p) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                return JSON.dumps(data.get("result"), ensure_ascii=False, indent=4)
            else:
                self.logger.error(f"GET request failed: {data}")
                raise Exception("GET request failed")

    async def get_new(self, url:str, params:dict[str, Any] | None = None) -> str:
        access_token = await self.get_access_token()
        p = {"access_token": access_token}
        if params is not None:
            p.update(params)

        async with self.session.get(url, params=p) as response:
            if response.status != 200:
                self.logger.error(f"GET request failed with status code: {response.status}")
                raise Exception(f"GET request failed with status code: {response.status}")

            data = await response.json()
            return JSON.dumps(data, ensure_ascii=False, indent=4)


    async def post_old(self, url:str, 
                   params:dict[str, Any] | None = None, 
                   json: Any | None = None) -> str:
        access_token = await self.get_access_token()

        p = {"access_token": access_token}
        if params is not None:
            p.update(params)

        logging.info(f"POST request URL: {json}")
        async with self.session.post(url, params=p, json=json) as response:
            data = await response.json()
            if data.get("errcode") == 0:
                return JSON.dumps(data.get("result"), ensure_ascii=False, indent=4)
            else:
                self.logger.error(f"POST request failed: {data}")
                raise Exception(f"POST request failed: {str(data)}")
            
    async def post_new(self, url:str,
                       params:dict[str, Any] | None = None,
                       json: Any | None = None) -> str: 
        access_token = await self.get_access_token()

        self.session.headers["x-acs-dingtalk-access-token"] = access_token
        self.session.headers["Content-Type"] = "application/json"

        logging.info(f"POST request URL: {json}")
        async with self.session.post(url, params=params, json=json) as response:
            if response.status != 200:
                self.logger.error(f"POST request failed with status code: {response.status}, {response.text}")
                raise Exception(f"POST request failed with status code: {response.status}, {response.text}")

            data = await response.json()
            return JSON.dumps(data, ensure_ascii=False, indent=4)