import sys
import os
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from linkedin_interactive_login import (
    sync_cookies_from_brave_cdp,
    save_storage_state_atomically,
    STORAGE_STATE_FILE
)

def monitor_and_capture(timeout_sec: int = 180):
    print("=" * 70)
    print("  CAPTURA Y PERSISTENCIA PERMANENTE DE SESIÓN LINKEDIN (1 AÑO)")
    print("=" * 70)
    print(f"Buscando sesión activa en Brave Browser (puerto 9222)...")
    print(f"Destino canónico: {STORAGE_STATE_FILE}")
    print("-" * 70)

    # 1. Intento inicial inmediato
    if sync_cookies_from_brave_cdp():
        print("✅ ¡SESIÓN ACTIVA DETECTADA Y GUARDADA CON ÉXITO!")
        print(f"Cookies de sesión 'li_at' y 'JSESSIONID' normalizadas a .linkedin.com.")
        print(f"Respaldo creado en: {STORAGE_STATE_FILE.with_suffix('.json.bak')}")
        return True

    print("⚠️ No hay sesión activa de LinkedIn en Brave en este momento.")
    print("👉 Por favor, ve a tu navegador Brave, entra a https://www.linkedin.com/login")
    print("   e inicia sesión con tu cuenta.")
    print(f"⏳ Esperando inicio de sesión (tiempo máximo: {timeout_sec}s)...")

    start_t = time.time()
    last_dot = 0
    while time.time() - start_t < timeout_sec:
        time.sleep(2.0)
        if sync_cookies_from_brave_cdp():
            print("\n" + "=" * 70)
            print("🎉 ¡SESIÓN CAPTURADA EXITOSAMENTE TRAS EL LOGIN!")
            print(f"✅ Archivo principal: {STORAGE_STATE_FILE}")
            print(f"✅ Respaldo permanente: {STORAGE_STATE_FILE.with_suffix('.json.bak')}")
            print(f"✅ Vigencia configurada: 1 año")
            print("=" * 70)
            return True
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\n❌ Tiempo de espera agotado sin detectar inicio de sesión en Brave.")
    return False

if __name__ == "__main__":
    t = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    success = monitor_and_capture(t)
    sys.exit(0 if success else 1)
