import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 3 });

test('cart test 2', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#email', 'shared-qa@example.com');
  await page.fill('#password', process.env.E2E_PASSWORD!);
  await page.click('.btn-primary');

  await page.goto('/products/blue-mug');
  await page.locator('.btn-primary').nth(2).click();
  await page.waitForTimeout(2000);
  expect(await page.locator('.toast-success').isVisible()).toBe(true);

  page.locator('[data-qa="cart-link"]').click();
  expect(await page.locator('.cart-row').count()).toBe(1);
});
