from main import anonymize_text, audit_text


def test_anonymization():
    print("Testing anonymization...")

    # Test cases
    cases = [
        (
            "Меня зовут Иван Петров, мой паспорт 4500 123456.",
            ["<PERSON>", "<PASSPORT_RF>"],
        ),
        (
            "Мой телефон +7 900 123 45 67 и email test@example.com",
            ["<PHONE>", "<EMAIL>"],
        ),
        ("ИНН компании 7707083893", ["<INN>"]),
        ("Мой telegram chat_id 123456789.", ["<TG_CHAT_ID>"]),
        ("Группа в телеграм с id -1001234567890", ["<TG_CHAT_ID>"]),
        ("Водительское удостоверение 9900 123456", ["<DRIVER_LICENSE>"]),
        ("Полис ОМС 1234567890123456", ["<OMS>"]),
        ("Машина с госномером А 123 АА 777", ["<CAR_PLATE>"]),
    ]

    for text, expected_tokens in cases:
        result = anonymize_text(text)
        print(f"Original: {text}")
        print(f"Result:   {result}")

        for token in expected_tokens:
            if token not in result:
                print(f"FAILED: Expected token {token} not found in result.")
            else:
                print(f"PASSED: Token {token} found.")
        print("-" * 20)


if __name__ == "__main__":
    test_anonymization()
