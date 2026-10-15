# Example: Delivery Instructions step

`Vendor_DeliveryNotes` adds a step between Shipping Method and Payment: a text area for instructions to the courier and
a "leave the package at the door" checkbox. The values are saved on the quote and copied to the order.

```
app/code/Vendor/DeliveryNotes/
├── composer.json                  requires oocscommerce/module-lynx-checkout
├── etc/
│   ├── module.xml
│   ├── db_schema.xml (+ db_schema_whitelist.json)
│   ├── fieldset.xml
│   ├── di.xml                     the step component (global)
│   └── frontend/di.xml            the heading plugin
├── i18n/en_US.csv
├── Plugin/AddStepHeading.php
├── Provider/DeliveryNotes.php
├── registration.php
└── view/frontend/lynx/
    ├── vue/src/Components/Checkout/Step/DeliveryNotes.vue
    └── react/src/Components/Checkout/Step/DeliveryNotes.tsx
```

## Module and storage

`etc/module.xml`:

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Module/etc/module.xsd">
    <module name="Vendor_DeliveryNotes">
        <sequence>
            <module name="OOCS_LynxCheckout"/>
        </sequence>
    </module>
</config>
```

`etc/db_schema.xml`:

```xml
<?xml version="1.0"?>
<schema xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Setup/Declaration/Schema/etc/schema.xsd">
    <table name="quote">
        <column xsi:type="text" name="vendor_delivery_instructions" nullable="true" comment="Delivery Instructions"/>
        <column xsi:type="smallint" name="vendor_leave_at_door" unsigned="true" nullable="false" default="0"
                comment="Leave At Door"/>
    </table>
    <table name="sales_order">
        <column xsi:type="text" name="vendor_delivery_instructions" nullable="true" comment="Delivery Instructions"/>
        <column xsi:type="smallint" name="vendor_leave_at_door" unsigned="true" nullable="false" default="0"
                comment="Leave At Door"/>
    </table>
</schema>
```

`bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_DeliveryNotes`

`etc/fieldset.xml` (quote fields copied to the order at placement):

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:DataObject/etc/fieldset.xsd">
    <scope id="global">
        <fieldset id="sales_convert_quote">
            <field name="vendor_delivery_instructions">
                <aspect name="to_order"/>
            </field>
            <field name="vendor_leave_at_door">
                <aspect name="to_order"/>
            </field>
        </fieldset>
    </scope>
</config>
```

Admin order view, emails and REST output of the values are the module's job, as for any order attribute.

## The provider - `Provider/DeliveryNotes.php`

```php
<?php
declare(strict_types=1);

namespace Vendor\DeliveryNotes\Provider;

use Magento\Checkout\Model\Session as CheckoutSession;
use Magento\Framework\Exception\LocalizedException;
use Magento\Quote\Api\CartRepositoryInterface;
use OOCS\LynxCheckout\Api\CheckoutStepInterface;
use OOCS\LynxComponent\Model\AbstractComponentProvider;

class DeliveryNotes extends AbstractComponentProvider implements CheckoutStepInterface
{
    private const MAX_LENGTH = 250;
    private const FIELD_INSTRUCTIONS = 'vendor_delivery_instructions';
    private const FIELD_LEAVE_AT_DOOR = 'vendor_leave_at_door';

    /**
     * @param CheckoutSession $checkoutSession
     * @param CartRepositoryInterface $quoteRepository
     */
    public function __construct(
        private readonly CheckoutSession $checkoutSession,
        private readonly CartRepositoryInterface $quoteRepository,
    ) {
    }

    /**
     * Fetched when the shopper reaches the step; every step must be optional
     *
     * @param array $props
     * @return bool
     */
    public function optional(array $props): bool
    {
        return true;
    }

    /**
     * What the quote holds, so going back or reloading shows the saved values
     *
     * @param array $props the posted draft
     * @return array
     */
    public function resolve(array $props): array
    {
        $quote = $this->checkoutSession->getQuote();

        $props['instructions'] = (string) $quote->getData(self::FIELD_INSTRUCTIONS);
        $props['leave_at_door'] = (bool) $quote->getData(self::FIELD_LEAVE_AT_DOOR);
        $props['max_length'] = self::MAX_LENGTH;
        $props['labels'] = [
            'instructions' => (string) __('Instructions for the courier'),
            'leaveAtDoor' => (string) __('Leave the package at the door'),
            'tooLong' => (string) __('Please enter less or equal than %1 symbols.', self::MAX_LENGTH),
            'none' => (string) __('None'),
            'edit' => (string) __('Edit'),
        ];

        return $props;
    }

    /**
     * Write the step's values to the quote, unless it already holds them
     *
     * @param array $draft
     * @return void
     * @throws LocalizedException
     */
    public function save(array $draft): void
    {
        $instructions = $draft['vendorDeliveryInstructions'] ?? null;
        $quote = $this->checkoutSession->getQuote();

        if (!\is_string($instructions) || !$quote->getId() || $quote->isVirtual()) {
            return;
        }

        $instructions = trim($instructions);
        $leaveAtDoor = !empty($draft['vendorLeaveAtDoor']) ? 1 : 0;

        if (mb_strlen($instructions) > self::MAX_LENGTH) {
            throw new LocalizedException(__('Please enter less or equal than %1 symbols.', self::MAX_LENGTH));
        }

        if ((string) $quote->getData(self::FIELD_INSTRUCTIONS) === $instructions
            && (int) $quote->getData(self::FIELD_LEAVE_AT_DOOR) === $leaveAtDoor
        ) {
            return;
        }

        $quote->setData(self::FIELD_INSTRUCTIONS, $instructions !== '' ? $instructions : null);
        $quote->setData(self::FIELD_LEAVE_AT_DOOR, $leaveAtDoor);
        $this->quoteRepository->save($quote);
    }
}
```

`i18n/en_US.csv` (the other phrases are Magento's own):

```csv
"Delivery Instructions","Delivery Instructions"
"Instructions for the courier","Instructions for the courier"
"Leave the package at the door","Leave the package at the door"
```

## The heading - `Plugin/AddStepHeading.php` + `etc/frontend/di.xml`

```php
<?php
declare(strict_types=1);

namespace Vendor\DeliveryNotes\Plugin;

use OOCS\LynxCheckout\Provider\Checkout\Checkout;

class AddStepHeading
{
    /**
     * Add the step's heading to the container's labels
     *
     * @param Checkout $subject
     * @param array $result
     * @return array
     */
    public function afterResolve(Checkout $subject, array $result): array
    {
        $result['labels']['deliveryInstructions'] = (string) __('Delivery Instructions');

        return $result;
    }
}
```

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:ObjectManager/etc/config.xsd">
    <type name="OOCS\LynxCheckout\Provider\Checkout\Checkout">
        <plugin name="vendor_deliverynotes_step_heading" type="Vendor\DeliveryNotes\Plugin\AddStepHeading"/>
    </type>
</config>
```

## Registering the step - `etc/di.xml` (global)

As in SKILL.md step 2: item `vendor_checkout_step_delivery_notes`, `component`
`Vendor_DeliveryNotes::Components/Checkout/Step/DeliveryNotes`, `group` `checkout_step`, `provider`
`Vendor\DeliveryNotes\Provider\DeliveryNotes\Proxy`, `zones` `content`, `available_on` `checkout_index_index`,
`settings` empty array.

## The component

The card follows the built-in steps: heading always, form while current, summary with **Edit** once done. Values live
in the component and are seeded from the quote whenever the provider answers.

### Vue - `Components/Checkout/Step/DeliveryNotes.vue`

```vue
<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useCheckoutStore } from 'OOCS_LynxCheckout/stores/checkoutStore'
import { useAnalyticsStore } from 'OOCS_LynxTheme/stores/global/analyticsStore'

// From Provider\DeliveryNotes, undefined until the step is first reached
const props = withDefaults(
    defineProps<{
        instructions?: string
        leave_at_door?: boolean
        max_length?: number
        labels?: Record<string, string>
    }>(),
    { instructions: undefined, leave_at_door: false, max_length: 250, labels: () => ({}) }
)

const checkout = useCheckoutStore()
const form = reactive({ instructions: '', leaveAtDoor: false })
const error = ref('')

const step = checkout.register({
    title: checkout.labels.deliveryInstructions ?? '',
    skip: checkout.isVirtual,
    data: () => ({ vendorDeliveryInstructions: form.instructions.trim(), vendorLeaveAtDoor: form.leaveAtDoor }),
})

// Seed from the quote whenever the provider answers
watch(
    () => [props.instructions, props.leave_at_door] as const,
    ([instructions, leaveAtDoor]) => {
        if (instructions === undefined) return
        form.instructions = instructions
        form.leaveAtDoor = leaveAtDoor
    },
    { immediate: true }
)

function submit() {
    error.value = form.instructions.trim().length > props.max_length ? (props.labels.tooLong ?? '') : ''
    if (error.value) return
    // Optional: an event of your own on the analytics bus
    useAnalyticsStore().track('vendor_delivery_instructions', { leave_at_door: form.leaveAtDoor })
    checkout.nextStep()
}
</script>

<template>
    <div
        v-if="!checkout.isVirtual"
        :data-step="step.index"
        :class="checkout.stepCardClass"
    >
        <h2
            class="text-lg font-semibold text-base-content"
            :class="step.isReached.value ? 'pb-3 mb-4 border-b border-base-300' : ''"
        >
            <template v-if="checkout.appearance.stepNumbering && step.number.value">{{ step.number.value }}. </template
            >{{ checkout.labels.deliveryInstructions }}
        </h2>

        <div
            v-if="step.isDone.value"
            class="flex items-start justify-between gap-3 rounded-box border-(length:--border) border-base-300 p-3"
        >
            <div class="text-base text-base-content/80">
                <p v-if="form.leaveAtDoor" class="font-semibold text-base-content">{{ labels.leaveAtDoor }}</p>
                <p v-if="form.instructions" class="whitespace-pre-line">{{ form.instructions }}</p>
                <p v-if="!form.leaveAtDoor && !form.instructions">{{ labels.none }}</p>
            </div>
            <button
                type="button"
                class="-m-2 p-2 bg-transparent border-none cursor-pointer text-sm font-semibold text-link"
                @click="checkout.goTo(step.index)"
            >
                {{ labels.edit }}
            </button>
        </div>

        <template v-else-if="step.isCurrent.value">
            <div v-if="step.loading.value" class="l-skeleton h-32 w-full" aria-busy="true"></div>

            <div v-else class="grid gap-4">
                <label class="grid gap-1">
                    <span class="text-base font-semibold text-base-content">{{ labels.instructions }}</span>
                    <textarea
                        v-model="form.instructions"
                        rows="3"
                        :maxlength="max_length"
                        :class="['l-textarea w-full', error ? 'l-textarea-error' : '']"
                    ></textarea>
                </label>
                <p v-if="error" data-checkout-error class="text-sm text-error">{{ error }}</p>

                <label class="flex items-center gap-3 cursor-pointer">
                    <input
                        v-model="form.leaveAtDoor"
                        type="checkbox"
                        class="l-checkbox l-checkbox-xs l-checkbox-primary shrink-0"
                    />
                    <span class="text-base text-base-content">{{ labels.leaveAtDoor }}</span>
                </label>
            </div>

            <button type="button" :class="checkout.stepButtonClass" :disabled="step.loading.value" @click="submit">
                {{ step.continueLabel.value }}
            </button>
        </template>
    </div>
</template>
```

### React - `Components/Checkout/Step/DeliveryNotes.tsx`

```tsx
import { useEffect, useState } from 'react'
import { useCheckoutStore } from 'OOCS_LynxCheckout/stores/checkoutStore'
import { useAnalyticsStore } from 'OOCS_LynxTheme/stores/global/analyticsStore'

// From Provider\DeliveryNotes, undefined until the step is first reached
type Props = {
    instructions?: string
    leave_at_door?: boolean
    max_length?: number
    labels?: Record<string, string>
}

const EMPTY_MAP: Record<string, never> = {}

export default function DeliveryNotes({
    instructions,
    leave_at_door = false,
    max_length = 250,
    labels = EMPTY_MAP,
}: Props) {
    const checkout = useCheckoutStore()
    // A store is a hook: read it here, use it in submit()
    const analytics = useAnalyticsStore()
    const [text, setText] = useState('')
    const [leaveAtDoor, setLeaveAtDoor] = useState(false)
    const [error, setError] = useState('')

    // Seed from the quote whenever the provider answers
    useEffect(() => {
        if (instructions === undefined) return
        setText(instructions)
        setLeaveAtDoor(leave_at_door)
    }, [instructions, leave_at_door])

    // Called on every render; the store keeps the latest data()
    const step = checkout.register({
        title: checkout.labels.deliveryInstructions ?? '',
        skip: checkout.isVirtual,
        data: () => ({ vendorDeliveryInstructions: text.trim(), vendorLeaveAtDoor: leaveAtDoor }),
    })

    function submit() {
        const message = text.trim().length > max_length ? (labels.tooLong ?? '') : ''
        setError(message)
        if (message) return
        analytics.track('vendor_delivery_instructions', { leave_at_door: leaveAtDoor })
        checkout.nextStep()
    }

    if (checkout.isVirtual) return null

    return (
        <div
            data-step={step.index}
            className={checkout.stepCardClass}
        >
            <h2
                className={`text-lg font-semibold text-base-content ${step.isReached ? 'pb-3 mb-4 border-b border-base-300' : ''}`}
            >
                {checkout.appearance.stepNumbering && step.number ? `${step.number}. ` : null}
                {checkout.labels.deliveryInstructions}
            </h2>

            {step.isDone ? (
                <div className="flex items-start justify-between gap-3 rounded-box border-(length:--border) border-base-300 p-3">
                    <div className="text-base text-base-content/80">
                        {leaveAtDoor && <p className="font-semibold text-base-content">{labels.leaveAtDoor}</p>}
                        {text && <p className="whitespace-pre-line">{text}</p>}
                        {!leaveAtDoor && !text && <p>{labels.none}</p>}
                    </div>
                    <button
                        type="button"
                        className="-m-2 p-2 bg-transparent border-none cursor-pointer text-sm font-semibold text-link"
                        onClick={() => checkout.goTo(step.index)}
                    >
                        {labels.edit}
                    </button>
                </div>
            ) : step.isCurrent ? (
                <>
                    {step.loading ? (
                        <div className="l-skeleton h-32 w-full" aria-busy="true"></div>
                    ) : (
                        <div className="grid gap-4">
                            <label className="grid gap-1">
                                <span className="text-base font-semibold text-base-content">{labels.instructions}</span>
                                <textarea
                                    value={text}
                                    onChange={event => setText(event.target.value)}
                                    rows={3}
                                    maxLength={max_length}
                                    className={`l-textarea w-full ${error ? 'l-textarea-error' : ''}`}
                                />
                            </label>
                            {error && (
                                <p data-checkout-error className="text-sm text-error">
                                    {error}
                                </p>
                            )}

                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={leaveAtDoor}
                                    onChange={event => setLeaveAtDoor(event.target.checked)}
                                    className="l-checkbox l-checkbox-xs l-checkbox-primary shrink-0"
                                />
                                <span className="text-base text-base-content">{labels.leaveAtDoor}</span>
                            </label>
                        </div>
                    )}

                    <button
                        type="button"
                        className={checkout.stepButtonClass}
                        disabled={step.loading}
                        onClick={submit}
                    >
                        {step.continueLabel}
                    </button>
                </>
            ) : null}
        </div>
    )
}
```

The browser check and `maxlength` are for the shopper's convenience; `save()` enforces the limit.

`track()` hands the event to every tracker registered with `addTracker()`. The built-in Google Tag node forwards only
its own nine GA4 events (each behind an `event_<name>` toggle) and drops others, so a custom event reaches an analytics
service only through a tracker that forwards it; see **forms-analytics** for the event bus.
