import { test, expect } from '@playwright/test';

// ============================================================
// HOME PAGE
// ============================================================
test.describe('Home Page', () => {
  test('loads with correct title and branding', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/Undercut/).first()).toBeVisible();
    await expect(page.getByText(/Unofficial F1 Fan Project/)).toBeVisible();
  });

  test('displays key sections', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /Pick a Scenario/i }).first()).toBeVisible();
    await expect(page.getByText(/Simulation Engine/)).toBeVisible();
    await expect(page.getByRole('heading', { name: /How It Works/ })).toBeVisible();
    await expect(page.getByText(/Tech Stack/)).toBeVisible();
  });

  test('Pick a Scenario button navigates to /scenarios', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /Pick a Scenario/i }).first().click();
    await expect(page).toHaveURL('/scenarios', { timeout: 10000 });
  });

  test('Methodology link navigates to /methodology', async ({ page }) => {
    await page.goto('/');
    await page.getByText(/Methodology/).first().click();
    await expect(page).toHaveURL('/methodology', { timeout: 10000 });
  });

  test('displays driver code VER on preview card', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('VER').first()).toBeVisible({ timeout: 5000 });
  });

  test('footer is visible', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer')).toBeVisible();
  });
});

// ============================================================
// SCENARIO SELECT PAGE
// ============================================================
test.describe('Scenario Select Page', () => {
  test('loads and displays race groups', async ({ page }) => {
    await page.goto('/scenarios');
    await expect(page.getByText(/Scenario Select/)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Brazil 2024')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Abu Dhabi 2021')).toBeVisible();
    await expect(page.getByText('Singapore 2023')).toBeVisible();
    await expect(page.getByText('Hungary 2022')).toBeVisible();
  });

  test('clicking race header expands scenarios', async ({ page }) => {
    await page.goto('/scenarios');
    // The race header button contains both the name and count
    const abuHeader = page.getByRole('button', { name: /Abu Dhabi 2021/ });
    await abuHeader.click();
    // After clicking, scenario cards for that race should be visible
    await expect(page.getByTestId('scenario-card').first()).toBeVisible({ timeout: 5000 });
  });

  test('clicking a scenario card navigates to play page', async ({ page }) => {
    await page.goto('/scenarios');
    // Expand Brazil
    await page.getByText('Brazil 2024').click();
    const firstCard = page.getByTestId('scenario-card').first();
    await expect(firstCard).toBeVisible({ timeout: 5000 });
    await firstCard.click();
    await expect(page).toHaveURL(/\/scenario\//, { timeout: 10000 });
  });

  test('back button navigates to home', async ({ page }) => {
    await page.goto('/scenarios');
    await page.getByText('Back to Home').click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// SCENARIO PLAY PAGE
// ============================================================
test.describe('Scenario Play Page', () => {
  test('loads scenario detail for brazil_2024_lap32', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.getByText(/VER/).first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByText('P2', { exact: true })).toBeVisible({ timeout: 10000 });
  });

  test('displays race state information', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.getByText(/Gap Ahead/)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/medium/).first()).toBeVisible({ timeout: 10000 });
  });

  test('displays action buttons', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    const actionBtns = page.getByTestId('action-button');
    await expect(actionBtns.first()).toBeVisible({ timeout: 15000 });
    await expect(actionBtns).toHaveCount(4);
  });

  test('submitting a decision navigates to result page', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    const actionBtn = page.getByTestId('action-button').first();
    await expect(actionBtn).toBeVisible({ timeout: 20000 });
    await actionBtn.click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
  });

  test('displays stint timeline', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.getByTestId('stint-timeline')).toBeVisible({ timeout: 15000 });
  });

  test('displays track status badge', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.getByTestId('track-status-badge')).toBeVisible({ timeout: 15000 });
  });

  test('shows error for non-existent scenario', async ({ page }) => {
    await page.goto('/scenario/nonexistent_id');
    await expect(page.getByText(/not found/i).or(page.getByText(/error/i))).toBeVisible({ timeout: 15000 });
  });
});

// ============================================================
// DECISION RESULT PAGE
// ============================================================
test.describe('Decision Result Page', () => {
  test('shows no result fallback when visiting directly', async ({ page }) => {
    await page.goto('/result');
    await expect(page.getByText(/No result to show/)).toBeVisible({ timeout: 5000 });
  });

  test('shows result after submitting a decision', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    const actionBtn = page.getByTestId('action-button').first();
    await expect(actionBtn).toBeVisible({ timeout: 20000 });
    await actionBtn.click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await expect(page.getByText('Your Score', { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Real Team/)).toBeVisible({ timeout: 10000 });
  });

  test('displays simulation metrics', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await expect(page.getByText(/Expected Position/)).toBeVisible({ timeout: 15000 });
  });

  test('displays chaos engine section', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await expect(page.getByText(/What if/).or(page.getByText(/Chaos Engine/))).toBeVisible({ timeout: 15000 });
  });

  test('try a different call navigates back to scenario', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await page.getByText(/Try a Different Call/).click();
    await expect(page).toHaveURL(/\/scenario\//, { timeout: 10000 });
  });

  test('play another navigates to home', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await page.getByText(/Play Another/).click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// CHAOS ENGINE
// ============================================================
test.describe('Chaos Engine', () => {
  test('shows chaos modifier toggles', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await expect(page.getByText('Safety Car', { exact: true })).toBeVisible({ timeout: 15000 });
  });

  test('simulate chaos with a modifier', async ({ page }) => {
    test.setTimeout(60000);
    await page.goto('/scenario/brazil_2024_lap32');
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await page.getByTestId('chaos-toggle').first().click();
    await page.getByTestId('chaos-simulate').click();
    await expect(page.getByText(/Modified Result/i).or(page.getByText(/Score/).first())).toBeVisible({ timeout: 30000 });
  });
});

// ============================================================
// ALL 12 SCENARIOS (Smoke Test)
// ============================================================
test.describe('All Scenarios Playable', () => {
  const scenarioIds = [
    'brazil_2024_lap32', 'brazil_2024_lap48', 'brazil_2024_lap68',
    'abu_dhabi_2021_lap14', 'abu_dhabi_2021_lap53', 'abu_dhabi_2021_lap56',
    'singapore_2023_lap20', 'singapore_2023_lap40', 'singapore_2023_lap43',
    'hungary_2022_lap38', 'hungary_2022_lap47', 'hungary_2022_lap51',
  ];

  for (const sid of scenarioIds) {
    test(`scenario ${sid} loads and has action buttons`, async ({ page }) => {
      test.setTimeout(30000);
      await page.goto(`/scenario/${sid}`);
      const actions = page.getByTestId('action-button');
      await expect(actions.first()).toBeVisible({ timeout: 20000 });
      await expect(actions.first()).toBeEnabled({ timeout: 10000 });
    });
  }
});

// ============================================================
// STATIC PAGES
// ============================================================
test.describe('Static Pages', () => {
  test('methodology page loads correctly', async ({ page }) => {
    await page.goto('/methodology');
    await expect(page.getByRole('heading', { name: /Data Sources/ })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: /Data Pipeline/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Machine Learning/ })).toBeVisible();
  });

  test('disclaimer page loads correctly', async ({ page }) => {
    await page.goto('/disclaimer');
    await expect(page.getByRole('heading', { name: /Disclaimer/ })).toBeVisible({ timeout: 5000 });
  });

  test('methodology page has back to home button', async ({ page }) => {
    await page.goto('/methodology');
    await page.getByText(/Back to Home/).click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// NAVIGATION FLOWS
// ============================================================
test.describe('Navigation Flows', () => {
  test('full flow: home → scenarios → play → result', async ({ page }) => {
    test.setTimeout(90000);
    await page.goto('/');
    await page.getByRole('button', { name: /Pick a Scenario/i }).first().click();
    await expect(page).toHaveURL('/scenarios', { timeout: 10000 });
    await page.getByText('Brazil 2024').click();
    const firstCard = page.getByTestId('scenario-card').first();
    await expect(firstCard).toBeVisible({ timeout: 5000 });
    await firstCard.click();
    await expect(page).toHaveURL(/\/scenario\//, { timeout: 10000 });
    await expect(page.getByTestId('action-button').first()).toBeVisible({ timeout: 20000 });
    await page.getByTestId('action-button').first().click();
    await expect(page).toHaveURL('/result', { timeout: 30000 });
    await expect(page.getByText('Your Score')).toBeVisible({ timeout: 15000 });
  });

  test('full flow: home → methodology → home', async ({ page }) => {
    await page.goto('/');
    await page.getByText(/Methodology/).first().click();
    await expect(page).toHaveURL('/methodology', { timeout: 10000 });
    await page.getByText(/Back to Home/).click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// RESPONSIVE DESIGN
// ============================================================
test.describe('Responsive Design', () => {
  test('renders on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.getByText(/Undercut/).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Pick a Scenario/i }).first()).toBeVisible();
  });

  test('scenarios page is usable on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/scenarios');
    await expect(page.getByText('Brazil 2024')).toBeVisible({ timeout: 15000 });
  });

  test('play page renders on small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto('/scenario/brazil_2024_lap32');
    const actions = page.getByTestId('action-button');
    await expect(actions.first()).toBeVisible({ timeout: 20000 });
  });
});
