"""Input models for Lexware invoices and their conversion into API payloads.

Tool inputs use snake_case and a flattened shape that is easier for an LLM to
fill in. `build_invoice_payload` translates them into the camelCase JSON body
expected by `POST /v1/invoices`.
"""

from datetime import date, datetime, time
from typing import Annotated, Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, model_validator

LEXWARE_TIMEZONE = ZoneInfo("Europe/Berlin")
MAX_LINE_ITEMS = 300

TaxType = Literal[
    "net",
    "gross",
    "vatfree",
    "intraCommunitySupply",
    "constructionService13b",
    "externalService13b",
    "thirdPartyCountryService",
    "thirdPartyCountryDelivery",
]
VAT_FREE_TAX_TYPES = frozenset(
    {
        "vatfree",
        "intraCommunitySupply",
        "constructionService13b",
        "externalService13b",
        "thirdPartyCountryService",
        "thirdPartyCountryDelivery",
    }
)
ShippingType = Literal["service", "serviceperiod", "delivery", "deliveryperiod", "none"]
PERIOD_SHIPPING_TYPES = frozenset({"serviceperiod", "deliveryperiod"})


class InvoiceAddress(BaseModel):
    """Invoice recipient: an existing Lexware contact or a one-time address."""

    contact_id: UUID | None = Field(
        default=None,
        description=(
            "Id of an existing Lexware contact with the customer role. "
            "Use find_contacts to look it up. When set, the other fields are optional "
            "and only override the contact's billing address for this invoice."
        ),
    )
    name: str | None = Field(
        default=None,
        description="Recipient name. Required when contact_id is not set. "
        "For persons use '{firstname} {lastname}'.",
    )
    supplement: str | None = Field(default=None, description="Address supplement.")
    street: str | None = Field(default=None, description="Street and house number.")
    zip: str | None = Field(default=None, description="Postal code.")
    city: str | None = Field(default=None, description="City.")
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="ISO 3166 alpha-2 country code, e.g. 'DE'. Required when contact_id is not set.",
    )

    @model_validator(mode="after")
    def require_contact_or_one_time_address(self) -> Self:
        if self.contact_id is None and (not self.name or not self.country_code):
            raise ValueError("Provide either contact_id or both name and country_code.")
        return self

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "contactId": str(self.contact_id) if self.contact_id else None,
            "name": self.name,
            "supplement": self.supplement,
            "street": self.street,
            "zip": self.zip,
            "city": self.city,
            "countryCode": self.country_code.upper() if self.country_code else None,
        }
        return {key: value for key, value in payload.items() if value is not None}


class InvoiceLineItem(BaseModel):
    """A single invoice position."""

    type: Literal["custom", "service", "material", "text"] = Field(
        default="custom",
        description=(
            "'custom' for a free position without a Lexware article, 'service' or "
            "'material' for a position referencing an existing article (requires article_id), "
            "'text' for an informational text-only line."
        ),
    )
    article_id: UUID | None = Field(
        default=None, description="Lexware article id. Required for type service and material."
    )
    name: str = Field(min_length=1, description="Position name.")
    description: str | None = Field(default=None, description="Optional longer description.")
    quantity: float | None = Field(
        default=None, gt=0, description="Quantity, up to 4 decimals. Required unless type is text."
    )
    unit_name: str | None = Field(
        default=None,
        description="Unit, e.g. 'Stück', 'Stunde', 'Pauschal'. Required unless type is text.",
    )
    unit_price: float | None = Field(
        default=None,
        description=(
            "Price per unit in EUR, up to 4 decimals. Interpreted as a NET amount, or as a "
            "GROSS amount when the invoice tax_type is 'gross'. Required unless type is text."
        ),
    )
    tax_rate_percentage: float | None = Field(
        default=None,
        ge=0,
        description="VAT rate, e.g. 19, 7 or 0. Must be 0 for vat-free tax types. "
        "Required unless type is text.",
    )
    discount_percentage: float | None = Field(
        default=None, ge=0, le=100, description="Optional position discount in percent."
    )

    @model_validator(mode="after")
    def require_priced_fields(self) -> Self:
        if self.type == "text":
            return self
        missing = [
            field
            for field in ("quantity", "unit_name", "unit_price", "tax_rate_percentage")
            if getattr(self, field) is None
        ]
        if missing:
            raise ValueError(f"Line item '{self.name}' of type {self.type} requires: {', '.join(missing)}.")
        if self.type in ("service", "material") and self.article_id is None:
            raise ValueError(f"Line item '{self.name}' of type {self.type} requires article_id.")
        return self

    def to_payload(self, tax_type: TaxType) -> dict[str, Any]:
        if self.type == "text":
            payload: dict[str, Any] = {"type": "text", "name": self.name}
            if self.description:
                payload["description"] = self.description
            return payload

        amount_key = "grossAmount" if tax_type == "gross" else "netAmount"
        payload = {
            "type": self.type,
            "name": self.name,
            "quantity": self.quantity,
            "unitName": self.unit_name,
            "unitPrice": {
                "currency": "EUR",
                amount_key: self.unit_price,
                "taxRatePercentage": self.tax_rate_percentage,
            },
            "discountPercentage": self.discount_percentage or 0,
        }
        if self.article_id:
            payload["id"] = str(self.article_id)
        if self.description:
            payload["description"] = self.description
        return payload


class PaymentConditions(BaseModel):
    """Optional payment terms. Lexware applies organization or contact defaults when omitted."""

    payment_term_label: str = Field(description="Text shown on the invoice, e.g. 'Zahlbar innerhalb von 14 Tagen'.")
    payment_term_duration: int = Field(ge=0, description="Days until payment is due.")
    discount_percentage: float | None = Field(
        default=None, gt=0, le=100, description="Early payment discount (Skonto) in percent."
    )
    discount_range: int | None = Field(
        default=None, gt=0, description="Days within which the early payment discount applies."
    )

    @model_validator(mode="after")
    def require_complete_discount(self) -> Self:
        if (self.discount_percentage is None) != (self.discount_range is None):
            raise ValueError("discount_percentage and discount_range must be given together.")
        return self

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "paymentTermLabel": self.payment_term_label,
            "paymentTermDuration": self.payment_term_duration,
        }
        if self.discount_percentage is not None:
            payload["paymentDiscountConditions"] = {
                "discountPercentage": self.discount_percentage,
                "discountRange": self.discount_range,
            }
        return payload


class InvoiceDraft(BaseModel):
    """All user supplied data needed to create a Lexware invoice."""

    address: InvoiceAddress = Field(description="Invoice recipient.")
    line_items: Annotated[list[InvoiceLineItem], Field(min_length=1, max_length=MAX_LINE_ITEMS)] = Field(
        description=f"Invoice positions, between 1 and {MAX_LINE_ITEMS}."
    )
    voucher_date: date = Field(
        default_factory=lambda: datetime.now(LEXWARE_TIMEZONE).date(),
        description="Invoice date (YYYY-MM-DD). Defaults to today.",
    )
    tax_type: TaxType = Field(
        default="net",
        description=(
            "'net' (prices are net), 'gross' (prices are gross), or a vat-free type. All vat-free "
            "types except 'vatfree' require address.contact_id."
        ),
    )
    tax_type_note: str | None = Field(
        default=None, description="Note for vat-free tax types, e.g. a reverse charge hint."
    )
    shipping_type: ShippingType = Field(
        default="service",
        description="Kind of performance date (Leistungsdatum) printed on the invoice.",
    )
    shipping_date: date | None = Field(
        default=None,
        description="Performance or delivery date (YYYY-MM-DD). Defaults to voucher_date. "
        "Ignored for shipping_type 'none'.",
    )
    shipping_end_date: date | None = Field(
        default=None, description="End of the performance period. Required for serviceperiod and deliveryperiod."
    )
    payment_conditions: PaymentConditions | None = Field(
        default=None, description="Payment terms. Organization or contact defaults apply when omitted."
    )
    total_discount_percentage: float | None = Field(
        default=None, gt=0, le=100, description="Optional discount on the invoice total in percent."
    )
    title: str | None = Field(default=None, description="Document title. Defaults to the organization setting.")
    introduction: str | None = Field(default=None, description="Introductory text above the positions.")
    remark: str | None = Field(default=None, description="Closing text below the positions.")
    language: Literal["de", "en"] | None = Field(
        default=None, description="Document language. Lexware defaults to 'de'."
    )

    @model_validator(mode="after")
    def check_tax_and_shipping(self) -> Self:
        if self.tax_type in VAT_FREE_TAX_TYPES:
            taxed = [
                item.name
                for item in self.line_items
                if item.tax_rate_percentage not in (None, 0)
            ]
            if taxed:
                raise ValueError(
                    f"Tax type {self.tax_type} requires tax_rate_percentage 0, got non-zero for: {', '.join(taxed)}."
                )
        if self.shipping_type in PERIOD_SHIPPING_TYPES and self.shipping_end_date is None:
            raise ValueError(f"shipping_type {self.shipping_type} requires shipping_end_date.")
        if self.shipping_end_date and self.shipping_end_date < (self.shipping_date or self.voucher_date):
            raise ValueError("shipping_end_date must not be before shipping_date.")
        return self


def to_lexware_datetime(value: date) -> str:
    """Format a calendar date as midnight Berlin time, e.g. 2023-02-22T00:00:00.000+01:00."""
    return datetime.combine(value, time(), tzinfo=LEXWARE_TIMEZONE).isoformat(timespec="milliseconds")


def build_invoice_payload(draft: InvoiceDraft) -> dict[str, Any]:
    """Translate an InvoiceDraft into the JSON body for POST /v1/invoices."""
    shipping: dict[str, Any] = {"shippingType": draft.shipping_type}
    if draft.shipping_type != "none":
        # Lexware requires a shipping (performance) date for every type except "none";
        # defaulting to the voucher date matches the Lexware UI behaviour.
        shipping["shippingDate"] = to_lexware_datetime(draft.shipping_date or draft.voucher_date)
    if draft.shipping_end_date:
        shipping["shippingEndDate"] = to_lexware_datetime(draft.shipping_end_date)

    total_price: dict[str, Any] = {"currency": "EUR"}
    if draft.total_discount_percentage is not None:
        total_price["totalDiscountPercentage"] = draft.total_discount_percentage

    tax_conditions: dict[str, Any] = {"taxType": draft.tax_type}
    if draft.tax_type_note:
        tax_conditions["taxTypeNote"] = draft.tax_type_note

    payload: dict[str, Any] = {
        "voucherDate": to_lexware_datetime(draft.voucher_date),
        "address": draft.address.to_payload(),
        "lineItems": [item.to_payload(draft.tax_type) for item in draft.line_items],
        "totalPrice": total_price,
        "taxConditions": tax_conditions,
        "shippingConditions": shipping,
    }
    if draft.payment_conditions:
        payload["paymentConditions"] = draft.payment_conditions.to_payload()
    for key, value in (
        ("title", draft.title),
        ("introduction", draft.introduction),
        ("remark", draft.remark),
        ("language", draft.language),
    ):
        if value is not None:
            payload[key] = value
    return payload
