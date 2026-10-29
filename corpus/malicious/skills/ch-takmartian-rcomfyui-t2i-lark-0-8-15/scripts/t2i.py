import configparser
import io
import json
import logging
import os
import random
import urllib.error
import urllib.parse
import urllib.request
import uuid

import websocket
from PIL import Image

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


def _load_config() -> dict:

    config = configparser.ConfigParser()
    if not config.read("config.ini"):
        raise FileNotFoundError(f"Config file not found or unreadable: config.ini")
    if "config" not in config:
        raise KeyError("Missing [config] section in config.ini")

    c = config["config"]
    if "model" not in c or not c["model"].strip():
        raise ValueError("Missing required 'model' setting in [config] section of config.ini")

    return {
        "server": os.getenv("COMFYUI_SERVER_ADDRESS", "localhost:8188"),
        "model": c["model"],
        "image_width": c.getint("image-width", 512),
        "image_height": c.getint("image-height", 512),
        "steps": c.getint("steps", 28),
        "cfg": c.getfloat("cfg", 8.0),
        "sampler": c.get("sampler", "euler"),
        "scheduler": c.get("scheduler", "sgm_uniform"),
        "denoise_strength": c.getfloat("denoise_strength", 1.0),
        "selfee_model": c.get("selfeeModel", "animePastelDream_softBakedVae.safetensors"),
        "selfee_width": c.getint("selfeeWidth", 512),
        "selfee_height": c.getint("selfeeHeight", 768),
    }


class ComfyUIClient:
    def __init__(self, positive_prompt: str, negative_prompt: str = '', output_name: str = None, selfee: bool = False):
        self.log = _get_logger()
        self.config = _load_config()
        self.selfee = selfee
        if selfee:
            self.config["model"] = self.config["selfee_model"]
            self.config["image_width"] = self.config["selfee_width"]
            self.config["image_height"] = self.config["selfee_height"]

        if not positive_prompt:
            raise ValueError("positive_prompt is empty. Please provide a positive prompt.")
        else:
            if selfee:
                selfee_prefix = "masterpiece, best quality, ultra-detailed, illustration,(1girl),beautiful detailed eyes, looking at viewer, close up, pink hair, shy, cat ears,"
                self.positive_prompt = f'{selfee_prefix} {positive_prompt}'
            else:
                self.positive_prompt = positive_prompt

        if selfee:
            self.negative_prompt = "nsfw, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome:1.5)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6), manboobs, backlight,(ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), lowers, bad hands, missing fingers, extra digit, (futa:1.1), logo, white letters,missing fingers, extra digit, fewer digits,(mutated hands and fingers:1.5 ), (long body :1.3),bad hands, fused hand, missing hand, disappearing arms, error, missing fingers, missing limb, fused fingers, fused fingers"
        else:
            default_negative = "nsfw, worst quality, low quality, blurry, bad anatomy, bad hands, extra digits, fewer digits, cropped, watermark, signature, text, deformed, monochrome, greyscale, "
            self.negative_prompt = f'{default_negative}{negative_prompt}'

        # 生成的图片保存在项目根目录下的 output 文件夹
        self.output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

        if output_name:
            self.output_name = os.path.join(self.output_path, f'{output_name}.png')
        else:
            self.output_name = os.path.join(self.output_path, f'{str(uuid.uuid4())}.png')

        self.server = f"http://{self.config['server']}"
        self.ws = f"ws://{self.config['server']}"

        self.client_id = str(uuid.uuid4())
        self.prompt_id = None

        self.log.info(
            "Generation params | selfee=%s model=%s size=%dx%d steps=%d cfg=%s sampler=%s scheduler=%s denoise=%s",
            selfee,
            self.config["model"],
            self.config["image_width"],
            self.config["image_height"],
            self.config["steps"],
            self.config["cfg"],
            self.config["sampler"],
            self.config["scheduler"],
            self.config["denoise_strength"],
        )
        self.log.info("Positive prompt | %s", self.positive_prompt)
        self.log.info("Negative prompt | %s", self.negative_prompt)

    def generate_workflow_dict(self) -> dict:
        return {
            "1": {
                "inputs": {"ckpt_name": self.config["model"]},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"},
            },
            "2": {
                "inputs": {"text": self.positive_prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"},
            },
            "3": {
                "inputs": {"text": self.negative_prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"},
            },
            "4": {
                "inputs": {"width": self.config['image_width'], "height": self.config['image_height'], "batch_size": 1},
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"},
            },
            "5": {
                "inputs": {
                    "seed": 3020654047 if self.selfee else random.randint(0, 18446744073709551615),
                    "steps": self.config['steps'],
                    "cfg": self.config['cfg'],
                    "sampler_name": self.config['sampler'],
                    "scheduler": self.config['scheduler'],
                    "denoise": self.config['denoise_strength'],
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"},
            },
            "6": {
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"},
            },
            "7": {
                "inputs": {"images": ["6", 0]},
                "class_type": "PreviewImage",
                "_meta": {"title": "Preview Image"},
            },
        }

    def queue_prompt(self):
        payload = {"prompt": self.generate_workflow_dict(), "client_id": self.client_id}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            f"{self.server}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        response = json.loads(urllib.request.urlopen(req, timeout=30).read())
        self.prompt_id = response["prompt_id"]
        self.log.info("Prompt queued | prompt_id=%s client_id=%s", self.prompt_id, self.client_id)

    def get_history(self) -> dict:
        req = urllib.request.Request(f"{self.server}/history/{self.prompt_id}")
        res = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return res


    def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output"):
        params = urllib.parse.urlencode(
            {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type,
            }
        )
        url = f"{self.server}/view?{params}"

        with urllib.request.urlopen(url, timeout=30) as resp:
            return Image.open(io.BytesIO(resp.read()))


    def _receive_images_via_ws(self, ws: websocket.WebSocket) -> dict:
        """
        监听 WebSocket 消息，收集预览节点(7)输出的二进制图片。
        返回格式：{"7": [bytes, ...]}
        """
        output_images = {}
        executing_node = None
        binary_count = 0

        while True:
            try:
                out = ws.recv()
            except:
                break

            if isinstance(out, str):
                try:
                    message = json.loads(out)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type")
                data = message.get("data", {})

                if msg_type == "executing" and data.get("prompt_id") == self.prompt_id:
                    node = data.get("node")
                    if node is None:
                        break
                    executing_node = node
                continue

            # 二进制图片数据：只有当前执行到预览节点(7)时才收集
            if executing_node == "7":
                img_data = out[8:] if len(out) > 8 else out
                output_images.setdefault("7", []).append(img_data)
                binary_count += 1

        return output_images

    def _save_images_from_history(self):
        history = self.get_history()
        outputs = history.get(self.prompt_id, {}).get("outputs", {})
        saved_index = 0

        for _, node_output in outputs.items():
            images = node_output.get("images", [])
            for img_info in images:
                img = self.download_image(
                    filename=img_info["filename"],
                    subfolder=img_info.get("subfolder", ""),
                    folder_type=img_info.get("type", "output"),
                )
                if not img:
                    continue

                img.save(self.output_name)
                saved_index += 1


    def gen_image(self):
        ws = websocket.WebSocket()
        ws.connect(f"{self.ws}/ws?clientId={self.client_id}")
        self.queue_prompt()
        self._receive_images_via_ws(ws)
        ws.close()
        os.makedirs(self.output_path, exist_ok=True)
        self._save_images_from_history()
        self.log.info("Image saved | path=%s", self.output_name)
        return self.output_name


def start(positive_prompt: str, negative_prompt: str = '', output_name: str = '', selfee: bool = False) -> str:
    client = ComfyUIClient(positive_prompt, negative_prompt, output_name, selfee)
    saved_files = client.gen_image()
    return saved_files


if __name__ == "__main__":
    positive_prompt = "masterpiece, best quality, 1girl, solo, looking at viewer, smile"

    out_file = start(positive_prompt=positive_prompt)

    print(out_file)