from mcp.server.fastmcp import FastMCP
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from analyzer_setup import create_analyzer_engine
import logging

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server_152fz")

# Initialize Presidio Engines
# This might take a moment to load the Spacy model
logger.info("Initializing Presidio Analyzer Engine...")
analyzer = create_analyzer_engine()
anonymizer = AnonymizerEngine()
logger.info("Presidio Engines initialized.")

# Create MCP Server
mcp = FastMCP("152-FZ-Filter")


@mcp.tool()
def anonymize_text(text: str) -> str:
    """
    Anonymizes the input text by masking personal data (names, phones, passports, etc.)
    compliant with 152-FZ.

    Args:
        text: The raw text containing potential personal data.

    Returns:
        The anonymized text with sensitive entities replaced by placeholders (e.g., <PERSON>, <RU_PASSPORT>).
    """
    logger.info(f"Anonymizing text of length: {len(text)}")

    results = analyzer.analyze(text=text, language="ru")

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
        "RU_INT_PASSPORT": OperatorConfig("replace", {"new_value": "<PASSPORT_INT>"}),
        # --- Spacy Mappings ---
        "NORP": OperatorConfig("replace", {"new_value": "<GROUP>"}),
        "FAC": OperatorConfig("replace", {"new_value": "<LOC>"}),
        "GPE": OperatorConfig("replace", {"new_value": "<LOC>"}),
        "DEFAULT": OperatorConfig("replace", {"new_value": "<ANONYMIZED>"}),
    }

    anonymized_result = anonymizer.anonymize(
        text=text, analyzer_results=results, operators=operators
    )

    return anonymized_result.text


@mcp.tool()
def audit_text(text: str) -> str:
    """
    Analyzes the text and returns a report of detected personal data categories
    WITHOUT returning the sensitive values themselves. Useful for checking what
    will be masked.

    Args:
        text: The text to audit.

    Returns:
        A JSON-formatted string listing detected entity types and their counts/positions.
    """
    results = analyzer.analyze(text=text, language="ru")

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

    return str(report)


if __name__ == "__main__":
    # Standard entry point for FastMCP
    mcp.run()
