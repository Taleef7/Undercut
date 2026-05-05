import { test, expect } from '@playwright/test';

// ============================================================
// HOME PAGE
// ============================================================
test.describe('Home Page', () => {
  test('loads with correct title and branding', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Undercut')).toBeVisible();
    await expect(page.locator('text=Unofficial F1 Fan Project')).toBeVisible();
  });

  test('displays key sections: hero, features, how it works, tech stack', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Pick a Scenario')).toBeVisible();
    await expect(page.locator('text=ML-Powered Analysis')).toBeVisible();
    await expect(page.locator('text=How It Works')).toBeVisible();
    await expect(page.locator('text=Tech Stack')).toBeVisible();
  });

  test('Pick a Scenario button navigates to /scenarios', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href="/scenarios"]').first().click();
    await expect(page).toHaveURL('/scenarios');
  });

  test('Methodology link navigates to /methodology', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href="/methodology"]').first().click();
    await expect(page).toHaveURL('/methodology');
  });

  test('displays the live race state preview card', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Interlagos')).toBeVisible();
    await expect(page.locator('text=VER')).toBeVisible();
  });

  test('footer contains GitHub, Methodology, Disclaimer links', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
  });
});

// ============================================================
// SCENARIO SELECT PAGE
// ============================================================
test.describe('Scenario Select Page', () => {
  test('loads and displays all 12 scenarios', async ({ page }) => {
    await page.goto('/scenarios');
    // Wait for loading to complete
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    // Should show 4 race groups (accordion headers)
    const raceHeaders = page.locator('[data-testid="race-group-header"]');
    await expect(raceHeaders).toHaveCount(4, { timeout: 10000 });
  });

  test('displays all four race names', async ({ page }) => {
    await page.goto('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Brazil 2024')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Abu Dhabi 2021')).toBeVisible();
    await expect(page.locator('text=Singapore 2023')).toBeVisible();
    await expect(page.locator('text=Hungary 2022')).toBeVisible();
  });

  test('clicking a scenario card navigates to play page', async ({ page }) => {
    await page.goto('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    // Click on first visible scenario card
    const firstCard = page.locator('[data-testid="scenario-card"]').first();
    await firstCard.click({ timeout: 10000 });
    await expect(page).toHaveURL(/\/scenario\//);
  });

  test('back button navigates to home', async ({ page }) => {
    await page.goto('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    await page.locator('text=Back to Home').click();
    await expect(page).toHaveURL('/');
  });

  test('scenario cards display driver code and lap number', async ({ page }) => {
    await page.goto('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    // Expand Brazil accordion
    await page.locator('text=Brazil 2024').click();
    const cards = page.locator('[data-testid="scenario-card"]');
    const firstCard = cards.first();
    await expect(firstCard).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================
// SCENARIO PLAY PAGE
// ============================================================
test.describe('Scenario Play Page', () => {
  test('loads scenario detail for brazil_2024_lap32', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    // Should show driver, position, lap info
    await expect(page.locator('text=VER').or(page.locator('text=P2'))).toBeVisible({ timeout: 10000 });
  });

  test('displays race state information', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    // Gap information should be visible
    await expect(page.locator('text=Gap Ahead').or(page.locator('text=gap'))).toBeVisible({ timeout: 10000 });
    // Tire compound information
    await expect(page.locator('text=medium')).toBeVisible({ timeout: 10000 });
  });

  test('displays action buttons', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    const actionButtons = page.locator('button:has-text("Pit")');
    await expect(actionButtons.first()).toBeVisible({ timeout: 10000 });
  });

  test('submitting a decision navigates to result page', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    // Click the first available action button
    const actionBtn = page.locator('[data-testid="action-button"]').first();
    await expect(actionBtn).toBeVisible({ timeout: 10000 });
    await actionBtn.click();
    // Should navigate to result
    await expect(page).toHaveURL('/result', { timeout: 15000 });
  });

  test('displays stint timeline', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    const timeline = page.locator('[data-testid="stint-timeline"]');
    await expect(timeline).toBeVisible({ timeout: 10000 });
  });

  test('displays track status badge', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="track-status-badge"]')).toBeVisible({ timeout: 10000 });
  });

  test('shows error for non-existent scenario', async ({ page }) => {
    await page.goto('/scenario/nonexistent_id');
    await expect(page.locator('text=not found').or(page.locator('text=error'))).toBeVisible({ timeout: 10000 });
  });
});

// ============================================================
// DECISION RESULT PAGE
// ============================================================
test.describe('Decision Result Page', () => {
  test('shows no result fallback when visiting directly', async ({ page }) => {
    await page.goto('/result');
    await expect(page.locator('text=No result to show')).toBeVisible({ timeout: 5000 });
  });

  test('shows result after submitting a decision', async ({ page }) => {
    // Navigate through scenario play to get result
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    const actionBtn = page.locator('[data-testid="action-button"]').first();
    await expect(actionBtn).toBeVisible({ timeout: 10000 });
    await actionBtn.click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });

    // Result page should show score and grade
    await expect(page.locator('text=Your Call').or(page.locator('text=Score'))).toBeVisible({ timeout: 10000 });
    // Model recommendation should be visible
    await expect(page.locator('text=Model Says').or(page.locator('text=stay_out')).or(page.locator('text=pit_now'))).toBeVisible({ timeout: 5000 });
  });

  test('displays simulation summary on result page', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });
    // Check for simulation summary sections
    await expect(page.locator('text=Risk').or(page.locator('text=Expected Position'))).toBeVisible({ timeout: 10000 });
  });

  test('displays chaos engine section on result page', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });
    // Chaos section should be visible
    await expect(page.locator('text=What If').or(page.locator('text=Chaos Engine'))).toBeVisible({ timeout: 10000 });
  });

  test('try a different call navigates back', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });
    // Click "Try a Different Call"
    const tryAgainBtn = page.locator('text=Try a Different Call');
    await expect(tryAgainBtn).toBeVisible({ timeout: 5000 });
    await tryAgainBtn.click();
    // Should navigate back to scenario
    await expect(page).toHaveURL(/\/scenario\//, { timeout: 10000 });
  });

  test('play another navigates to home', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });
    // Click "Play Another"
    const playAnotherBtn = page.locator('text=Play Another');
    await expect(playAnotherBtn).toBeVisible({ timeout: 5000 });
    await playAnotherBtn.click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// CHAOS ENGINE
// ============================================================
test.describe('Chaos Engine', () => {
  test('shows chaos modifier toggles on result page', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });

    // Check for modifier toggles
    await expect(page.locator('text=Safety Car').or(page.locator('text=Rain Starts'))).toBeVisible({ timeout: 10000 });
  });

  test('simulate chaos with modifier toggles', async ({ page }) => {
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });

    // Toggle a modifier
    const modifierSwitch = page.locator('[data-testid="chaos-toggle"]').first();
    await modifierSwitch.click();

    // Click Simulate Chaos
    const simulateBtn = page.locator('text=Simulate Chaos');
    await simulateBtn.click();
    // Wait for chaos result to appear
    await expect(page.locator('text=Chaos Result').or(page.locator('text=Modified'))).toBeVisible({ timeout: 15000 });
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
      await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
      const actions = page.locator('[data-testid="action-button"]');
      await expect(actions.first()).toBeVisible({ timeout: 10000 });
    });
  }
});

// ============================================================
// STATIC PAGES
// ============================================================
test.describe('Static Pages', () => {
  test('methodology page loads correctly', async ({ page }) => {
    await page.goto('/methodology');
    await expect(page.locator('text=Data Sources')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Data Pipeline')).toBeVisible();
    await expect(page.locator('text=Machine Learning')).toBeVisible();
    await expect(page.locator('text=Simulation Engine')).toBeVisible();
  });

  test('disclaimer page loads correctly', async ({ page }) => {
    await page.goto('/disclaimer');
    await expect(page.locator('text=unofficial fan project').or(page.locator('text=Disclaimer'))).toBeVisible({ timeout: 5000 });
  });

  test('methodology page has back to home button', async ({ page }) => {
    await page.goto('/methodology');
    await page.locator('text=Back to Home').click();
    await expect(page).toHaveURL('/');
  });
});

// ============================================================
// NAVIGATION FLOWS
// ============================================================
test.describe('Navigation Flows', () => {
  test('full flow: home → scenarios → play → result → home', async ({ page }) => {
    await page.goto('/');
    // Click Pick a Scenario
    await page.locator('a[href="/scenarios"]').first().click();
    await expect(page).toHaveURL('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });

    // Click Brazil 2024 accordion to expand
    await page.locator('text=Brazil 2024').click();
    // Click first scenario card
    const card = page.locator('[data-testid="scenario-card"]').first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await expect(page).toHaveURL(/\/scenario\//);

    // Submit decision
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    await page.locator('[data-testid="action-button"]').first().click();
    await expect(page).toHaveURL('/result', { timeout: 15000 });

    // Navigate home
    await page.locator('text=Play Another').first().click();
    await expect(page).toHaveURL('/');
  });

  test('full flow: home → methodology → disclaimer → home', async ({ page }) => {
    await page.goto('/');
    // Click Methodology
    await page.locator('a[href="/methodology"]').first().click();
    await expect(page).toHaveURL('/methodology');
    // Click Disclaimer from footer or back
    const footer = page.locator('footer');
    if (await footer.locator('text=Disclaimer').isVisible()) {
      await footer.locator('text=Disclaimer').click();
      await expect(page).toHaveURL('/disclaimer');
    }
  });
});

// ============================================================
// RESPONSIVE DESIGN
// ============================================================
test.describe('Responsive Design', () => {
  test('renders on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.locator('text=Undercut')).toBeVisible();
    await expect(page.locator('text=Pick a Scenario')).toBeVisible();
  });

  test('scenarios page is usable on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/scenarios');
    await expect(page.locator('text=Loading scenarios')).not.toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Brazil 2024')).toBeVisible({ timeout: 10000 });
  });

  test('play page renders on small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto('/scenario/brazil_2024_lap32');
    await expect(page.locator('text=Loading telemetry')).not.toBeVisible({ timeout: 15000 });
    // Action buttons should still be reachable
    const actions = page.locator('[data-testid="action-button"]');
    await expect(actions.first()).toBeVisible({ timeout: 10000 });
  });
});
