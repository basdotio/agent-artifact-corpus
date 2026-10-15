---
name: checkout-step
description: Adds a custom step to the Lynx one-page checkout (OOCS_LynxCheckout) - a component in group `checkout_step` that the merchant places in the `before_shipping_method` or `before_payment` slot of the Checkout component, a step provider (`optional()` true, `resolve()` from the posted draft, idempotent `save()` via `OOCS\LynxCheckout\Api\CheckoutStepInterface`), a Vue and React component that calls `checkout.register({ title, skip, data, affectsTotals })` with its heading in `checkout.labels`, `data-step`, inline errors, virtual-cart skipping and an analytics event. Also covers changing the built-in steps with plugins. Use when a developer says "add a checkout step in Lynx", "delivery instructions / gift message / order comment / custom field step on the Lynx checkout", "ask every shopper something before payment", "save extra checkout data to the quote in Lynx", "plugin on a Lynx checkout step". For input tied to one carrier use shipping-method, to one payment method payment-method. Use with the basics skill.
---

# Lynx checkout step

Produces a new step of the Lynx checkout: registry entry (global `etc/di.xml`), a step provider that saves to the
quote, a heading label added to the container, and the step component in Vue and React. The merchant places the step
in PageBuilder; the storage and the copy to the order are plain Magento.

## Before you start

- Read **basics** (module layout, aliases, build), **component** (registry keys) and **provider**
  (`AbstractComponentProvider`, `optional()`).
- Check a smaller fit first: input for one carrier -> **shipping-method**; for one payment method ->
  **payment-method**; content next to the checkout -> a normal component in the Checkout's **Below Order
  Summary** slot (`sidebar_after`). A step is for a question every shopper answers before paying.
- Changing a built-in step does not need a new step - see "Modifying the built-in steps" below.
- Code to imitate (in `vendor/oocscommerce/module-lynx-checkout`):
  `Provider/Checkout/Step/ShippingMethod.php` (save that returns early), `Controller/Checkout/Process.php` (the flow),
  `view/frontend/lynx/vue/src/Components/Checkout/Step/ShippingMethod.vue` and the React `.tsx` twin (card markup),
  `view/frontend/lynx/<vue|react>/src/stores/checkoutStore.ts` (`register`, `StepHandle`).

## How the flow works

```
Checkout (default_checkout)
├── express        express payment buttons
├── before_shipping_method   extra steps between Address and Shipping Method
├── before_payment           extra steps between Shipping Method and Payment
└── sidebar_after  content below the order summary
```

1. Address, Shipping Method and Payment are fixed: the container renders them, they are not layout nodes. It gets
   `steps` (the fixed names with the visible nodes of each slot between them) and `steps_url`
   (`/lynx/checkout/process`) from `OOCS\LynxCheckout\Provider\Checkout\Checkout`. Steps whose component the
   current theme lacks are dropped on the client (a module shipping only `.vue` is skipped on a React theme).
2. Each step component calls `checkout.register(...)`. The flow starts once **every** step in `steps` has registered,
   at the first one not skipped.
3. Moving to a step (Continue, Edit, page load, an Inertia reload of the step) POSTs
   `{ form_key, step: <target node name>, steps: [taking-part names], data: <merge of every step's data()> }`.
4. `Controller\Checkout\Process`: looks up the target's provider in the component registry; missing or
   `optional()` not true -> 404, nothing saved. Then the step **right before the target** in `steps`: if its provider
   implements `CheckoutStepInterface` (and is optional), `save($data)`. Then `resolve($data)` of the target -> JSON
   props, put on the page under the target's node name.
5. A `LocalizedException` from `save()` or `resolve()` answers `{ "error": "..." }`; the store shows it and moves the
   shopper back to the step before the target. If the saved step registered `affectsTotals`, totals are re-read.
6. Payment is last and has no `save()`: it posts `payment-information` itself.

## Steps

### 1. Module wiring

`etc/module.xml` sequences `OOCS_LynxCheckout`; `composer.json` requires `oocscommerce/module-lynx-checkout`.
Storage: quote + `sales_order` columns in `etc/db_schema.xml` (+ whitelist) and `etc/fieldset.xml`
(`sales_convert_quote` -> `to_order`). Full files in [reference/delivery-notes-example.md](reference/delivery-notes-example.md).

### 2. Register the step - global `etc/di.xml`

```xml
<type name="OOCS\LynxComponent\Model\Registry">
    <arguments>
        <argument name="components" xsi:type="array">
            <item name="vendor_checkout_step_delivery_notes" xsi:type="array">
                <item name="component" xsi:type="string">Vendor_DeliveryNotes::Components/Checkout/Step/DeliveryNotes</item>
                <item name="group" xsi:type="string">checkout_step</item>
                <item name="icon" xsi:type="string">ph-note-pencil</item>
                <item name="provider" xsi:type="object">Vendor\DeliveryNotes\Provider\DeliveryNotes\Proxy</item>
                <item name="label" xsi:type="string">Delivery Instructions</item>
                <item name="description" xsi:type="string">Instructions for the courier and a leave-at-door choice, saved on the order</item>
                <item name="zones" xsi:type="array">
                    <item name="content" xsi:type="string">content</item>
                </item>
                <item name="available_on" xsi:type="array">
                    <item name="checkout" xsi:type="string">checkout_index_index</item>
                </item>
                <item name="settings" xsi:type="array"/>
            </item>
        </argument>
    </arguments>
</type>
```

`group` must be `checkout_step` (the only group the **Before Shipping Method** and **Before Payment** slots accept,
once per component). The registered name
is the name `Process` and the store look the step up by.

### 3. The provider - `Provider/DeliveryNotes.php`

```php
class DeliveryNotes extends AbstractComponentProvider implements CheckoutStepInterface
{
    /** Every step must be optional: left out of the page, fetched when reached */
    public function optional(array $props): bool
    {
        return true;
    }

    /** $props is the posted draft, not the node settings */
    public function resolve(array $props): array
    {
        $quote = $this->checkoutSession->getQuote();
        $props['instructions'] = (string) $quote->getData('vendor_delivery_instructions');
        $props['labels'] = ['instructions' => (string) __('Instructions for the courier'), 'edit' => (string) __('Edit')];
        return $props;
    }

    /** Runs each time the step after this one is fetched: validate, compare, write only on change */
    public function save(array $draft): void
    {
        $value = $draft['vendorDeliveryInstructions'] ?? null;
        $quote = $this->checkoutSession->getQuote();
        if (!\is_string($value) || !$quote->getId() || $quote->isVirtual()) {
            return;
        }
        // validate -> throw new LocalizedException(__('...')) to send the shopper back to this step
        if ((string) $quote->getData('vendor_delivery_instructions') === trim($value)) {
            return;
        }
        $quote->setData('vendor_delivery_instructions', trim($value));
        $this->quoteRepository->save($quote);
    }
}
```

(Abbreviated; the complete class with constructor, docblocks and length check is in the reference.)

| Method | When | Receives |
|---|---|---|
| `optional()` - return `true` | On the page (props left out) and as `Process`'s check | Node settings on the page, the draft in a step request |
| `resolve()` | Only in a step request, when the step becomes current | The posted draft (`data`), **not** node settings |
| `save()` (`OOCS\LynxCheckout\Api\CheckoutStepInterface`) | In the request fetching the step **after** this one | The same draft |

A step with no data of its own still needs a provider returning `true` from `optional()` (and its labels).

### 4. The heading - plugin on the container provider

The heading shows from the first paint, before the step's own props arrive, so it lives in the container's labels.

```php
namespace Vendor\DeliveryNotes\Plugin;

use OOCS\LynxCheckout\Provider\Checkout\Checkout;

class AddStepHeading
{
    public function afterResolve(Checkout $subject, array $result): array
    {
        $result['labels']['deliveryInstructions'] = (string) __('Delivery Instructions');
        return $result;
    }
}
```

`etc/frontend/di.xml`:

```xml
<type name="OOCS\LynxCheckout\Provider\Checkout\Checkout">
    <plugin name="vendor_deliverynotes_step_heading" type="Vendor\DeliveryNotes\Plugin\AddStepHeading"/>
</type>
```

### 5. The component

`view/frontend/lynx/vue/src/Components/Checkout/Step/DeliveryNotes.vue` and
`view/frontend/lynx/react/src/Components/Checkout/Step/DeliveryNotes.tsx`. Complete Vue + React code:
[reference/delivery-notes-example.md](reference/delivery-notes-example.md#the-component).

```ts
const checkout = useCheckoutStore() // from 'OOCS_LynxCheckout/stores/checkoutStore'
const step = checkout.register({
    title: checkout.labels.deliveryInstructions ?? '', // feeds the previous step's "Continue to ..."
    skip: checkout.isVirtual,                          // only if the step is about shipping
    data: () => ({ vendorDeliveryInstructions: form.instructions.trim() }),
    // affectsTotals: true                             // if save() changes totals
})
```

- Vue: call `register()` once in `<script setup>`; the handle's flags are computed refs (`step.isDone.value`).
  React: call it on **every render** (the store dedupes); flags are plain values (`step.isDone`). The store finds the
  node name itself (parent node in Vue, `CheckoutStepContext` provided by the container in React).
- `register()` returns `{ index, isCurrent, isReached, isDone, loading, continueLabel }`.

Card contract (copy the built-in steps' markup and classes):

- Root: `:data-step="step.index"` (the store scrolls to it and focuses its `h2`), classes
  `checkout.stepCardClass` (card or flat, as the merchant set **Step Style** on the Checkout component).
- `h2` heading from `checkout.labels.<yourKey>` always, prefixed `{step.number}. ` when
  `checkout.appearance.stepNumbering` and `step.number` (0 while skipped); border under it once `isReached`.
- `isDone`: a collapsed summary + **Edit** button -> `checkout.goTo(step.index)`.
- `isCurrent`: skeleton while `loading`, else the form, then the Continue button
  (`:class="checkout.stepButtonClass"`, text `step.continueLabel`, disabled while `loading`).
- Not reached: heading only.
- Seed the form from the provider props each time they arrive (they are `undefined` until first reached).
- Continue: validate in the browser, show inline errors marked `data-checkout-error`, then optionally
  `useAnalyticsStore().track('<your_event>', {...})` (`OOCS_LynxTheme/stores/global/analyticsStore`; in React call the
  hook at the top of the component), then `checkout.nextStep()`.
- Inputs: `checkout.inputClass(invalid)` or daisyUI `l-input` / `l-textarea` / `l-checkbox` classes.

Other store members: `prevStep()`, `goTo(index)`, `labels`, `isVirtual`, `draft` (fixed `CheckoutDraft` shape - keep
your own values in the component), `refreshTotals()`.

### 6. Build, install, place

```bash
bin/magento module:enable Vendor_DeliveryNotes && bin/magento setup:upgrade
bin/magento lynx:workspace:setup OOCS_LynxVue OOCS_LynxReact
bin/magento lynx:static:deploy
bin/magento lynx:compile        # if the store uses compiled config
bin/magento cache:clean
```

The step appears only once the merchant places it: PageBuilder > Checkout page > select **Checkout** > **Add to
Before Payment** (or **Before Shipping Method**) > the step, in the merchant's own design (the default design is
read-only). Put this in the module's install guide; never write the merchant's checkout layout from a data patch.

## Modifying the built-in steps

Address, Shipping Method and Payment are not layout nodes: the container renders them in that fixed order, their
registry entries are `hidden` (kept for `Process` to find the providers). Their look follows the Checkout component's
settings (**Steps** group: style, numbering, Continue width, how rates and methods are listed).

- Add props or change labels: `afterResolve` plugin on `OOCS\LynxCheckout\Provider\Checkout\Step\ShippingAddress`,
  `...\ShippingMethod` or `...\Payment`.
- Save more when a step is left: `beforeSave` plugin on `ShippingAddress` or `ShippingMethod` reading your keys from
  `$draft` (e.g. `OOCS\LynxInStorePickup\Plugin\SavePickupLocation`). `Payment` has no `save()`.
- Change markup: override the step's `.vue` / `.tsx` in a theme; keep `register()`, `data-step` and the `data()` keys
  the providers read (`shippingAddress`, `shippingMethod`...).
- Address fields: merchant setting **Address Fields** of the Checkout component; no code.

## Rules

- **Pick the slot by what the step reads.** In **Before Shipping Method** the address is already on the quote; in
  **Before Payment** the carrier is too and totals are recollected. Payment is always last.
- **Every node in `steps` must register**, even when it does not apply (`skip: true`); one that never registers keeps
  the checkout from starting. Skip in `register()`, then render nothing.
- **`save()` idempotent and cheap**: it reruns on Edit, back navigation and Inertia reloads. Compare with the quote,
  return early. Check `getId()` and `isVirtual()`.
- **`$draft` is browser input** and holds every step's data: check types/lengths, use vendor-prefixed keys that cannot
  clash (`vendorDeliveryInstructions`).
- **Reject with `LocalizedException`** and a translated message; the shopper returns to your step.
- **Node settings never reach the provider** in a step request; settings needing provider resolution (`_i18n`, `image`,
  `url`) are unusable on a step. Plain settings reach the component as props.
- **Unsaved input is lost on reload**: only the built-in draft fields persist in `localStorage`; the step re-reads the
  quote when reached again.
- **Registry entry global `etc/di.xml`**; the heading plugin may live in `etc/frontend/di.xml`.
- **No UI text in the component**; reuse Magento phrases ("Edit", "None", "Please enter less or equal than %1
  symbols.").
- **Ship `.vue` and `.tsx`** (a theme lacking the file skips the step). Tokens and `l-` classes only, nothing below
  `text-sm`. Load code with `import`; external scripts need `csp_whitelist.xml` and `checkout.cspNonce`.

## Check

- [ ] Guest and signed-in customer with saved addresses, on the Vue **and** React theme.
- [ ] Virtual cart: shipping-related step drops out, "Continue to ..." labels follow, `save()` inert.
- [ ] Edit each finished step and Continue again: values kept, no unnecessary writes.
- [ ] A value `save()` rejects: message shown, shopper back on your step.
- [ ] Reload mid-checkout: the step shows the saved value once reached.
- [ ] The placed order carries the values (`sales_order.<column>`).
- [ ] Editor preview of the Checkout page with the step added: the preview uses the admin browser's **real cart** (add
      a product first); steps added in the editor show before the layout is saved, and step requests save to that real
      quote.

## Reference

- [reference/delivery-notes-example.md](reference/delivery-notes-example.md) - complete Delivery Instructions module:
  storage, provider, heading plugin, registry, Vue + React component, translations.
- https://docs.oocscommerce.com/lynx/developer/checkout-steps
