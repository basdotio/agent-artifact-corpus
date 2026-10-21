"""Configure the external checkout's LLM in memory; never save its config.toml."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str = ''
    model: str = ''
    api_key: str = field(default='', repr=False)

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        provider = env.get('SHANIU_MPT_LLM_PROVIDER', 'compatible').strip().lower()
        if provider == 'upstream':
            return cls(provider)
        if provider != 'compatible':
            raise ValueError('SHANIU_MPT_LLM_PROVIDER must be compatible or upstream')
        base = env.get('SHANIU_MPT_LLM_API_BASE', 'https://maas-api.cn-huabei-1.xf-yun.com/v2').strip().rstrip('/')
        base = base.removesuffix('/chat/completions')
        model = env.get('SHANIU_MPT_LLM_MODEL', 'xopglm53').strip()
        key = (env.get('SHANIU_MPT_LLM_API_KEY') or env.get('SHANIU_API_KEY', '')).strip()
        parsed = urlsplit(base)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not (
            parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'})
        ):
            raise ValueError('MoneyPrinter LLM requires HTTPS, or local HTTP, without credentials/query in the URL')
        if not model or not key:
            raise ValueError('Configure SHANIU_MPT_LLM_MODEL and SHANIU_MPT_LLM_API_KEY (or SHANIU_API_KEY) in Shaniu/.env')
        return cls(provider, base, model, key)

    def apply(self, app_config):
        if self.provider == 'compatible':
            # MoneyPrinter already supports the OpenAI-compatible wire protocol.
            # Only the current process sees these values.
            app_config.update(llm_provider='openai', openai_base_url=self.base_url,
                              openai_model_name=self.model, openai_api_key=self.api_key)

    def public(self):
        if self.provider == 'upstream':
            return dict(provider=self.provider)
        return dict(provider=self.provider, api_base=self.base_url, model=self.model)


def load_config():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    return LLMConfig.from_env()
