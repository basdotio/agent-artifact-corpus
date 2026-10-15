import logging
import sys
from main import anonymize_text
from analyzer_setup import create_analyzer_engine

# Configure logging
logging.basicConfig(level=logging.ERROR)


def run_test(name, input_text, expected_tokens):
    print(f"Testing: {name}")
    print(f"Input:   {input_text}")

    try:
        result = anonymize_text(input_text)
        print(f"Result:  {result}")

        missing = []
        for token in expected_tokens:
            if token not in result:
                missing.append(token)

        if not missing:
            print("STATUS:  PASSED ✅")
            return True
        else:
            print(f"STATUS:  FAILED ❌ (Missing: {missing})")
            return False
    except Exception as e:
        print(f"STATUS:  ERROR ⚠️ ({e})")
        return False
    finally:
        print("-" * 40)


def main():
    print("=== Extended PII Verification ===\n")

    tests = [
        (
            "Digital Identifiers",
            "Мой IP: 192.168.1.1, MAC: 00:1A:2B:3C:4D:5E, IMEI: 123456789012345",
            ["<IP>", "<MAC>", "<IMEI>"],
        ),
        (
            "Financial Data",
            "Перевод на IBAN DE89370400440532013000 и CVV 123.",
            ["<BANK_ACCOUNT>", "<CVV>"],
        ),
        ("Geo Location", "Я нахожусь по координатам 55.755, 37.617.", ["<GEO>"]),
        ("Dates", "Я родился 01.01.1990 года.", ["<DATE>"]),
        (
            "International Passport",
            "Загранпаспорт 75 1234567 выдан ФМС.",
            ["<PASSPORT_INT>"],
        ),
        ("NORP (Nationality/Group)", "Русские и американцы встретились.", ["<GROUP>"]),
    ]

    passed = 0
    total = len(tests)

    for name, text, expected in tests:
        if run_test(name, text, expected):
            passed += 1

    print(f"\nSummary: {passed}/{total} tests passed.")

    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
