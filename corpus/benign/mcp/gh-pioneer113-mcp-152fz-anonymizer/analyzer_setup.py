import logging
from presidio_analyzer import (
    AnalyzerEngine,
    PatternRecognizer,
    Pattern,
    RecognizerRegistry,
)
from presidio_analyzer.nlp_engine import SpacyNlpEngine, NerModelConfiguration
from presidio_analyzer.predefined_recognizers import (
    SpacyRecognizer,
    EmailRecognizer,
    PhoneRecognizer,
    IpRecognizer,
    IbanRecognizer,
    CryptoRecognizer,
)

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyzer_setup")


def create_analyzer_engine():
    """
    Creates and configures the Presidio AnalyzerEngine with Russian language support
    and custom recognizers for Russian documents and Extended PII.
    """

    # 1. Setup NLP Engine (Spacy with ru_core_news_lg) using direct instantiation
    ner_config = NerModelConfiguration(
        labels_to_ignore=["O"],
        model_to_presidio_entity_mapping={
            "PER": "PERSON",
            "LOC": "LOCATION",
            "GPE": "LOCATION",  # Countries, cities, states
            "FAC": "LOCATION",  # Buildings, airports, highways
            "ORG": "ORGANIZATION",
            "NORP": "NORP",  # Nationalities, religious/political groups
            "MISC": "O",
        },
        low_score_entity_names=[],
    )

    nlp_engine = SpacyNlpEngine(
        models=[{"lang_code": "ru", "model_name": "ru_core_news_lg"}],
        ner_model_configuration=ner_config,
    )
    nlp_engine.load()

    # 2. Create Registry and Analyzer
    registry = RecognizerRegistry()

    # Standard Recognizers (Explicit 'ru' where applicable or 'en' if universal)
    registry.add_recognizer(SpacyRecognizer(supported_language="ru"))
    registry.add_recognizer(EmailRecognizer(supported_language="ru"))
    registry.add_recognizer(PhoneRecognizer(supported_language="ru"))
    registry.add_recognizer(IpRecognizer(supported_language="ru"))
    registry.add_recognizer(IbanRecognizer(supported_language="ru"))
    registry.add_recognizer(CryptoRecognizer(supported_language="ru"))

    # 3. Add Custom Recognizers

    # --- Digital Identifiers ---
    # MAC Address
    mac_pattern = Pattern(
        name="mac_pattern",
        regex=r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
        score=0.8,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="MAC_ADDRESS",
            patterns=[mac_pattern],
            supported_language="ru",
        )
    )

    # IMEI (15 digits usually)
    imei_pattern = Pattern(name="imei_pattern", regex=r"\b\d{15,17}\b", score=0.6)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="EME_IMEI",
            patterns=[imei_pattern],
            supported_language="ru",
            context=["imei", "device id"],
        )
    )

    # --- Financial ---
    # CVV/CVC
    cvv_pattern = Pattern(name="cvv_pattern", regex=r"\b\d{3,4}\b", score=0.6)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="CVV",
            patterns=[cvv_pattern],
            supported_language="ru",
            context=["cvv", "cvc", "cvv2", "cvc2", "код безопасности", "код карты"],
        )
    )

    # --- Legacy / Docs ---
    # --- Passport RF ---
    passport_rf_pattern = Pattern(
        name="passport_rf_pattern", regex=r"\b\d{4}[\s-]\d{6}\b", score=0.85
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_PASSPORT",
            patterns=[passport_rf_pattern],
            supported_language="ru",
        )
    )

    # --- International Passport RF (Zagran) ---
    # Series 2 digits, Number 7 digits.
    passport_int_pattern = Pattern(
        name="passport_int_pattern", regex=r"\b\d{2}[\s-]?\d{7}\b", score=0.85
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_INT_PASSPORT",
            patterns=[passport_int_pattern],
            supported_language="ru",
            context=[
                "загранпаспорт",
                "заграничный паспорт",
                "паспорт",
                "серия",
                "номер",
            ],
        )
    )

    # --- INN (Individual Taxpayer Number) ---
    inn_pattern_10 = Pattern(name="inn_10_pattern", regex=r"\b\d{10}\b", score=0.9)
    inn_pattern_12 = Pattern(name="inn_12_pattern", regex=r"\b\d{12}\b", score=0.9)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_INN",
            patterns=[inn_pattern_10, inn_pattern_12],
            supported_language="ru",
            context=["ИНН", "идентификационный номер"],
        )
    )

    # --- SNILS ---
    snils_pattern = Pattern(
        name="snils_pattern", regex=r"\b\d{3}-\d{3}-\d{3}[\s-]\d{2}\b", score=0.85
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_SNILS",
            patterns=[snils_pattern],
            supported_language="ru",
            context=["СНИЛС", "страховой номер"],
        )
    )

    # --- Driver's License (VU) ---
    vu_pattern = Pattern(
        name="vu_pattern", regex=r"\b\d{2}[А-Яа-я0-9]{2}\s*\d{6}\b", score=0.6
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_DRIVER_LICENSE",
            patterns=[vu_pattern],
            supported_language="ru",
            context=["водительское", "права", "в/у", "удостоверение"],
        )
    )

    # --- OMS (Medical Policy) ---
    oms_pattern = Pattern(name="oms_pattern", regex=r"\b\d{16}\b", score=0.6)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_OMS",
            patterns=[oms_pattern],
            supported_language="ru",
            context=["омс", "полис", "страховой"],
        )
    )

    # --- Vehicle Plate (GRZ) ---
    plate_pattern = Pattern(
        name="plate_pattern",
        regex=r"\b[ABEKMHOPCTYXАВЕКМНОРСТУХ]\s*\d{3}\s*[ABEKMHOPCTYXАВЕКМНОРСТУХ]{2}\s*\d{2,3}\b",
        score=0.7,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="RU_VEHICLE_PLATE",
            patterns=[plate_pattern],
            supported_language="ru",
            context=["госномер", "номер авто", "машина", "автомобиль", "грз"],
        )
    )

    # --- Telegram Chat ID ---
    # 1. Pattern for Channels/Supergroups (starts with -100)
    tg_channel_pattern = Pattern(
        name="tg_channel_pattern",
        regex=r"(?i)(?:id\s*)?(?<!\d)-100\d{10,}\b",
        score=1.0,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="TG_CHAT_ID",
            patterns=[tg_channel_pattern],
            supported_language="ru",
            context=["chat_id", "chatid", "телеграм", "telegram", "tg_id", "чат", "id"],
        )
    )

    # 2. General Pattern for user IDs
    tg_id_pattern = Pattern(name="tg_id_pattern", regex=r"(?<!\d)\d{5,15}\b", score=0.6)
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="TG_CHAT_ID",
            patterns=[tg_id_pattern],
            supported_language="ru",
            context=["chat_id", "chatid", "телеграм", "telegram", "tg_id", "чат", "id"],
        )
    )

    # --- Geo Coordinates ---
    # Matches: 55.123, 37.123 or 55.123N, 37.123E
    geo_pattern = Pattern(
        name="geo_pattern",
        regex=r"\b-?\d{1,3}\.\d{3,10}[,\s]+-?\d{1,3}\.\d{3,10}\b",
        score=0.6,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="GPS_COORDS",
            patterns=[geo_pattern],
            supported_language="ru",
            context=["gps", "координаты", "широта", "долгота", "location"],
        )
    )

    # --- Dates (Simple Regex) ---
    # DD.MM.YYYY, DD-MM-YYYY, YYYY-MM-DD
    date_pattern = Pattern(
        name="date_pattern",
        regex=r"\b(?:(?:0[1-9]|[12]\d|3[01])[./-](?:0[1-9]|1[0-2])[./-](?:19|20)\d{2}|(?:19|20)\d{2}[./-](?:0[1-9]|1[0-2])[./-](?:0[1-9]|[12]\d|3[01]))\b",
        score=0.6,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="DATE_TIME",
            patterns=[date_pattern],
            supported_language="ru",
            context=["дата", "родился", "число", "год"],
        )
    )

    # --- NORP (Nationalities fallback) ---
    # Convert common nationalities to regex for reliability if Spacy fails
    nationalities = [
        "русские",
        "американцы",
        "китайцы",
        "башкиры",
        "татары",
        "евреи",
        "армяне",
        "грузины",
        "украинцы",
        "белорусы",
        "немцы",
        "французы",
        "англичане",
        "испанцы",
        "итальянцы",
        "чеченцы",
        "дагестанцы",
    ]
    # Simple case-insensitive regex for demo purposes
    norp_regex = r"(?i)\b(" + "|".join(nationalities) + r")\b"
    norp_pattern = Pattern(name="norp_pattern", regex=norp_regex, score=0.6)

    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="NORP",
            patterns=[norp_pattern],
            supported_language="ru",
        )
    )

    # Create the engine
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)

    return analyzer
