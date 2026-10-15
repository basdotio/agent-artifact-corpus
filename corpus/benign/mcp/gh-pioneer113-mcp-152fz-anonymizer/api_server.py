import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from analyzer_setup import create_analyzer_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

# Load environment variables
load_dotenv()
# Load API keys from JSON file
API_KEYS_FILE = "api_keys.json"
api_keys_db = {}
request_counts = {}


def load_api_keys():
    global api_keys_db
    try:
        if os.path.exists(API_KEYS_FILE):
            with open(API_KEYS_FILE, "r") as f:
                data = json.load(f)
                api_keys_db = data.get("keys", {})
                logger.info(f"Loaded {len(api_keys_db)} API keys.")
        else:
            logger.warning(f"{API_KEYS_FILE} not found. Authentication might fail.")
    except Exception as e:
        logger.error(f"Failed to load API keys: {e}")


# Initial load
load_api_keys()

# Define security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header not in api_keys_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    user_data = api_keys_db[api_key_header]
    username = user_data.get("user", "Unknown")
    limit = user_data.get("limit", 0)

    # Simple in-memory rate limiting (per restart)
    current_count = request_counts.get(username, 0)
    if current_count >= limit:
        logger.warning(f"Rate limit exceeded for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    request_counts[username] = current_count + 1
    logger.info(
        f"Access granted for user: {username} ({request_counts[username]}/{limit})"
    )
    return api_key_header


app = FastAPI(
    title="152-FZ Anonymizer API",
    description="REST API for anonymizing Russian personal data suitable for n8n/Zapier integrations.",
    version="1.0.0",
)

# Initialize engines at startup
logger.info("Initializing Presidio engines...")
analyzer = create_analyzer_engine()
anonymizer = AnonymizerEngine()
logger.info("Engines ready.")


class AnonymizeRequest(BaseModel):
    text: str


class AnonymizeResponse(BaseModel):
    anonymized_text: str


class AuditResponse(BaseModel):
    entities: list


@app.post("/anonymize", response_model=AnonymizeResponse)
async def anonymize(request: AnonymizeRequest, token: str = Depends(get_api_key)):
    """
    Anonymize input text replacing PII with placeholders.
    """
    try:
        results = analyzer.analyze(text=request.text, language="ru")

        # Reuse the same operators as in main.py
        operators = {
            # --- Standard PII ---
            "RU_PASSPORT": OperatorConfig("replace", {"new_value": "<PASSPORT_RF>"}),
            "RU_SNILS": OperatorConfig("replace", {"new_value": "<SNILS>"}),
            "RU_INN": OperatorConfig("replace", {"new_value": "<INN>"}),
            "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
            "ORGANIZATION": OperatorConfig("replace", {"new_value": "<ORG>"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "<LOC>"}),
            "RU_DRIVER_LICENSE": OperatorConfig(
                "replace", {"new_value": "<DRIVER_LICENSE>"}
            ),
            "RU_OMS": OperatorConfig("replace", {"new_value": "<OMS>"}),
            "RU_VEHICLE_PLATE": OperatorConfig("replace", {"new_value": "<CAR_PLATE>"}),
            "TG_CHAT_ID": OperatorConfig("replace", {"new_value": "<TG_CHAT_ID>"}),
            # --- Extended PII ---
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP>"}),
            "IBAN_CODE": OperatorConfig("replace", {"new_value": "<BANK_ACCOUNT>"}),
            "CRYPTO": OperatorConfig("replace", {"new_value": "<WALLET>"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<BANK_CARD>"}),
            "CVV": OperatorConfig("replace", {"new_value": "<CVV>"}),
            "MAC_ADDRESS": OperatorConfig("replace", {"new_value": "<MAC>"}),
            "EME_IMEI": OperatorConfig("replace", {"new_value": "<IMEI>"}),
            "GPS_COORDS": OperatorConfig("replace", {"new_value": "<GEO>"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
            "RU_INT_PASSPORT": OperatorConfig(
                "replace", {"new_value": "<PASSPORT_INT>"}
            ),
            # --- Spacy Mappings ---
            "NORP": OperatorConfig("replace", {"new_value": "<GROUP>"}),
            "FAC": OperatorConfig("replace", {"new_value": "<LOC>"}),
            "GPE": OperatorConfig("replace", {"new_value": "<LOC>"}),
            "DEFAULT": OperatorConfig("replace", {"new_value": "<ANONYMIZED>"}),
        }

        anonymized_result = anonymizer.anonymize(
            text=request.text, analyzer_results=results, operators=operators
        )

        return AnonymizeResponse(anonymized_text=anonymized_result.text)

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit", response_model=AuditResponse)
async def audit(request: AnonymizeRequest, token: str = Depends(get_api_key)):
    """
    Return detected entities without modifying text.
    Requires X-API-Token header.
    """
    results = analyzer.analyze(text=request.text, language="ru")
    report = []
    for res in results:
        report.append(
            {
                "entity_type": res.entity_type,
                "start": res.start,
                "end": res.end,
                "score": res.score,
            }
        )
    return AuditResponse(entities=report)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
