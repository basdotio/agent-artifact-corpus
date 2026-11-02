import json
import logging
import requests
import os
from requests_toolbelt import MultipartEncoder

BASE_URL = os.getenv("LARK_BASE_URL", "https://open.larksuite.com")

_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "run.log")


def _get_logger():
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    logger = logging.getLogger("rcomfyui")
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(module)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def get_token():
    log = _get_logger()
    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")
    if not app_id or not app_secret:
        raise ValueError("LARK_APP_ID and LARK_APP_SECRET must be set in environment variables")

    url = f"{BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
    log.info("POST %s | app_id=%s", url, app_id)
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    log.info("Response %d | %s", resp.status_code, resp.text)
    resp.raise_for_status()
    [REDACTED_SECRET]).get("tenant_access_token")
    return token


class LarkImageSender:
    def __init__(self, chat_id=None, image_path=None):
        self.log = _get_logger()
        self.[REDACTED_SECRET])
        self.chat_id = chat_id
        self.image_path = image_path

    def upload_image(self, image_path):
        url = f"{BASE_URL}/open-apis/im/v1/images"
        self.log.info("POST %s | image_path=%s", url, image_path)
        with open(image_path, "rb") as f:
            form = {
                "image_type": "message",
                "image": f
            }
            multi_form = MultipartEncoder(form)
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": multi_form.content_type
            }
            response = requests.post(url, headers=headers, data=multi_form)
        self.log.info("Response %d | %s", response.status_code, response.text)
        response.raise_for_status()
        image_key = response.json().get("data", {}).get("image_key")
        return image_key

    def send_message(self):
        if self.chat_id.startswith("ou_"):
            receive_id_type = "open_id"
        else:
            receive_id_type = "chat_id"
        receive_id = self.chat_id

        url = f"{BASE_URL}/open-apis/im/v1/messages?receive_id_type={receive_id_type}"

        image_key = self.upload_image(self.image_path)

        payload = {
            "receive_id": receive_id,
            "content": json.dumps({
                "image_key": image_key,
                "alt": "Image"
            }),
            "msg_type": "image"
        }
        self.log.info(
            "POST %s | receive_id=%s receive_id_type=%s image_key=%s",
            url, receive_id, receive_id_type, image_key,
        )
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        self.log.info("Response %d | %s", response.status_code, response.text)
        response.raise_for_status()

        print('Image sent successfully!')
        return 'Image sent successfully!'


def start(image_path: str, chat_id: str = None):
    sender = LarkImageSender(chat_id=chat_id, image_path=image_path)
    return sender.send_message()