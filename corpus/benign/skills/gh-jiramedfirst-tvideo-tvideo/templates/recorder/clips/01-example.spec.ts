import { test, expect } from '@playwright/test';
import { tap, typeInto } from '../cursor';
import { createTimeline, hold } from '../timeline';

/**
 * Example clip for the repository's demo app (examples/demo-app, any static
 * server; TV_BASE_URL points at it). Replace with the real flow. The pattern
 * every clip follows:
 *  - createTimeline() is the first line (its t0 is the video's t=0);
 *  - every viewer-visible step is tl.step('<caption the viewer will read>', …);
 *  - every click/type goes through tap()/typeInto(): the cursor glides there
 *    (smooth-scrolling first if it's off-screen) and the click's time, box and
 *    whether the control vanished are logged — the editor's click sound,
 *    auto-ring and holdFirst come from that;
 *  - every step ENDS with an expect — the recording is also a test, so when the
 *    app's UI changes a re-record fails loudly instead of filming a broken flow;
 *  - hold() after key moments so the viewer can read the screen; glideTo() only
 *    to show something below the fold that isn't clicked.
 */
test('01 example: create an order', async ({ page }, testInfo) => {
  const tl = createTimeline(testInfo, page);

  await tl.step('Open the Orders page', async () => {
    await page.goto('');
    await expect(page.getByTestId('orders-table')).toBeVisible();
    await hold(page);
  });

  await tl.step('Click “+ New order”', async () => {
    await tap(page, page.getByTestId('new-order'));
    await expect(page.getByRole('heading', { name: 'New order' })).toBeVisible();
    await hold(page);
  });

  await tl.step('Choose the customer', async () => {
    await tap(page, page.getByTestId('customer').getByRole('button'));
    await expect(page.getByRole('listbox')).toBeVisible();
    await hold(page, 700);
    await tap(page, page.getByRole('option', { name: 'Northwind Traders' }));
    await expect(page.getByTestId('customer').getByRole('button')).toHaveText('Northwind Traders');
    await hold(page);
  });

  await tl.step('Enter the product and the quantity', async () => {
    await typeInto(page, page.getByLabel('Product *'), 'Coffee beans 1 kg');
    const qty = page.getByLabel('Quantity *');
    await tap(page, qty);
    await qty.fill('20');
    await expect(qty).toHaveValue('20');
    await hold(page);
  });

  await tl.step('Click “Save order” — the order appears in the list', async () => {
    await tap(page, page.getByRole('button', { name: 'Save order' }));
    await expect(page.getByRole('status')).toHaveText(/Order ORD-\d+ created/);
    await expect(page.getByTestId('orders-table')).toContainText('Coffee beans 1 kg');
    await hold(page, 2000);
  });

  await tl.save();
});
