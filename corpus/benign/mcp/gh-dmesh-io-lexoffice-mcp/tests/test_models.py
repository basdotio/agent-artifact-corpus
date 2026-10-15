from datetime import date

import pytest
from pydantic import ValidationError

from models import InvoiceAddress, InvoiceDraft, InvoiceLineItem, PaymentConditions, build_invoice_payload


def custom_item(**overrides) -> InvoiceLineItem:
    values = {
        "name": "Beratung",
        "quantity": 2,
        "unit_name": "Stunde",
        "unit_price": 100.0,
        "tax_rate_percentage": 19,
    }
    return InvoiceLineItem(**(values | overrides))


def one_time_address() -> InvoiceAddress:
    return InvoiceAddress(name="Bike & Ride GmbH", street="Musterstraße 42", zip="79112", city="Freiburg", country_code="de")


def test_builds_minimal_net_invoice_payload():
    draft = InvoiceDraft(address=one_time_address(), line_items=[custom_item()], voucher_date=date(2023, 2, 22))

    assert build_invoice_payload(draft) == {
        "voucherDate": "2023-02-22T00:00:00.000+01:00",
        "address": {
            "name": "Bike & Ride GmbH",
            "street": "Musterstraße 42",
            "zip": "79112",
            "city": "Freiburg",
            "countryCode": "DE",
        },
        "lineItems": [
            {
                "type": "custom",
                "name": "Beratung",
                "quantity": 2,
                "unitName": "Stunde",
                "unitPrice": {"currency": "EUR", "netAmount": 100.0, "taxRatePercentage": 19},
                "discountPercentage": 0,
            }
        ],
        "totalPrice": {"currency": "EUR"},
        "taxConditions": {"taxType": "net"},
        "shippingConditions": {"shippingType": "service", "shippingDate": "2023-02-22T00:00:00.000+01:00"},
    }


def test_uses_summer_time_offset():
    draft = InvoiceDraft(address=one_time_address(), line_items=[custom_item()], voucher_date=date(2023, 7, 1))

    assert build_invoice_payload(draft)["voucherDate"] == "2023-07-01T00:00:00.000+02:00"


def test_gross_tax_type_sends_gross_amount():
    draft = InvoiceDraft(
        address=one_time_address(), line_items=[custom_item()], voucher_date=date(2023, 2, 22), tax_type="gross"
    )

    unit_price = build_invoice_payload(draft)["lineItems"][0]["unitPrice"]
    assert unit_price == {"currency": "EUR", "grossAmount": 100.0, "taxRatePercentage": 19}


def test_contact_reference_only_sends_contact_id():
    address = InvoiceAddress(contact_id="e9066f04-8cc7-4616-93f8-ac9ecc8479c8")

    assert address.to_payload() == {"contactId": "e9066f04-8cc7-4616-93f8-ac9ecc8479c8"}


def test_text_item_and_optional_sections():
    draft = InvoiceDraft(
        address=one_time_address(),
        line_items=[
            custom_item(article_id="97b98491-e953-4dc9-97a9-ae437a8052b4", type="service", description="Remote"),
            InvoiceLineItem(type="text", name="Hinweis", description="Danke"),
        ],
        voucher_date=date(2023, 2, 22),
        shipping_type="serviceperiod",
        shipping_date=date(2023, 2, 1),
        shipping_end_date=date(2023, 2, 28),
        payment_conditions=PaymentConditions(
            payment_term_label="10 Tage 3 %, 30 Tage netto",
            payment_term_duration=30,
            discount_percentage=3,
            discount_range=10,
        ),
        total_discount_percentage=5,
        title="Rechnung",
        remark="Vielen Dank",
        language="en",
    )

    payload = build_invoice_payload(draft)

    assert payload["lineItems"][0]["id"] == "97b98491-e953-4dc9-97a9-ae437a8052b4"
    assert payload["lineItems"][0]["description"] == "Remote"
    assert payload["lineItems"][1] == {"type": "text", "name": "Hinweis", "description": "Danke"}
    assert payload["shippingConditions"] == {
        "shippingType": "serviceperiod",
        "shippingDate": "2023-02-01T00:00:00.000+01:00",
        "shippingEndDate": "2023-02-28T00:00:00.000+01:00",
    }
    assert payload["paymentConditions"] == {
        "paymentTermLabel": "10 Tage 3 %, 30 Tage netto",
        "paymentTermDuration": 30,
        "paymentDiscountConditions": {"discountPercentage": 3, "discountRange": 10},
    }
    assert payload["totalPrice"] == {"currency": "EUR", "totalDiscountPercentage": 5}
    assert payload["title"] == "Rechnung"
    assert payload["remark"] == "Vielen Dank"
    assert payload["language"] == "en"
    assert "introduction" not in payload


def test_shipping_type_none_omits_date():
    draft = InvoiceDraft(
        address=one_time_address(), line_items=[custom_item()], voucher_date=date(2023, 2, 22), shipping_type="none"
    )

    assert build_invoice_payload(draft)["shippingConditions"] == {"shippingType": "none"}


@pytest.mark.parametrize(
    "build",
    [
        lambda: InvoiceAddress(name="No country"),
        lambda: InvoiceAddress(country_code="DE"),
        lambda: custom_item(unit_price=None),
        lambda: custom_item(type="material"),
        lambda: PaymentConditions(payment_term_label="x", payment_term_duration=30, discount_percentage=2),
        lambda: InvoiceDraft(address=one_time_address(), line_items=[]),
        lambda: InvoiceDraft(address=one_time_address(), line_items=[custom_item()], tax_type="vatfree"),
        lambda: InvoiceDraft(address=one_time_address(), line_items=[custom_item()], shipping_type="deliveryperiod"),
        lambda: InvoiceDraft(
            address=one_time_address(),
            line_items=[custom_item()],
            voucher_date=date(2023, 2, 22),
            shipping_type="serviceperiod",
            shipping_end_date=date(2023, 2, 1),
        ),
    ],
    ids=[
        "address-missing-country",
        "address-missing-name",
        "item-missing-price",
        "material-missing-article",
        "incomplete-skonto",
        "no-line-items",
        "vatfree-with-tax-rate",
        "period-without-end",
        "end-before-start",
    ],
)
def test_rejects_invalid_input(build):
    with pytest.raises(ValidationError):
        build()
