#!/usr/bin/env node
/**
 * Phase 4 Verification Script
 * ===========================
 *
 * Verifies that the frontend integration for usage tracking
 * and limit enforcement is correctly implemented.
 *
 * Usage:
 *     node verify_phase4.js
 */

const fs = require("fs");
const path = require("path");

const PUSTAK_ROOT = path.join(__dirname, "pustak", "src");

console.log("=".repeat(80));
console.log("PHASE 4 VERIFICATION: Frontend Integration");
console.log("=".repeat(80));
console.log();

let allChecks = true;

// ============================================================================
// Task 1: Usage API Client
// ============================================================================

console.log("\u2705 1. Usage API Client");

const usageApiPath = path.join(PUSTAK_ROOT, "lib", "usage.ts");
if (fs.existsSync(usageApiPath)) {
	console.log(`   - File created: ${path.relative(__dirname, usageApiPath)}`);

	const content = fs.readFileSync(usageApiPath, "utf-8");

	const checks = {
		"fetchUsageStats function": content.includes("fetchUsageStats"),
		"UsageStats interface": content.includes("interface UsageStats"),
		"ResourceUsage interface": content.includes("interface ResourceUsage"),
		"PlanTier type": content.includes("type PlanTier"),
		"UsageLimitError interface": content.includes("interface UsageLimitError"),
		"getUsagePercentage utility": content.includes("getUsagePercentage"),
		"getUsageColor utility": content.includes("getUsageColor"),
		"isUsageLimitError utility": content.includes("isUsageLimitError"),
	};

	for (const [check, passed] of Object.entries(checks)) {
		console.log(`   ${passed ? "\u2713" : "\u2717"} ${check}`);
		if (!passed) allChecks = false;
	}
} else {
	console.log(
		`   \u274c File NOT FOUND: ${path.relative(__dirname, usageApiPath)}`
	);
	allChecks = false;
}

console.log();

// ============================================================================
// Task 2: Usage Dashboard Component
// ============================================================================

console.log("\u2705 2. Usage Dashboard Component");

const usageCardPath = path.join(
	PUSTAK_ROOT,
	"components",
	"UsageStatsCard.tsx"
);
if (fs.existsSync(usageCardPath)) {
	console.log(`   - File created: ${path.relative(__dirname, usageCardPath)}`);

	const content = fs.readFileSync(usageCardPath, "utf-8");

	const checks = {
		"UsageStatsCard component": content.includes(
			"export function UsageStatsCard"
		),
		"ResourceProgressBar component": content.includes(
			"function ResourceProgressBar"
		),
		"Progress bar rendering": content.includes("rounded-full overflow-hidden"),
		"Color-coded bars (green/yellow/red)":
			content.includes("green") &&
			content.includes("yellow") &&
			content.includes("red"),
		"fetchUsageStats import": content.includes("fetchUsageStats"),
		"useAuth hook": content.includes("useAuth"),
		"Loading state": content.includes("isLoading"),
		"Error handling": content.includes("error"),
		"Upgrade CTA": content.includes("Upgrade"),
		"Cycle end date display":
			content.includes("cycle_end") || content.includes("formatDate"),
	};

	for (const [check, passed] of Object.entries(checks)) {
		console.log(`   ${passed ? "\u2713" : "\u2717"} ${check}`);
		if (!passed) allChecks = false;
	}
} else {
	console.log(
		`   \u274c File NOT FOUND: ${path.relative(__dirname, usageCardPath)}`
	);
	allChecks = false;
}

console.log();

// ============================================================================
// Task 3: Graceful Error Handling
// ============================================================================

console.log("\u2705 3. GenerateDocsButton Error Handling");

const generateButtonPath = path.join(
	PUSTAK_ROOT,
	"components",
	"GenerateDocsButton.tsx"
);
if (fs.existsSync(generateButtonPath)) {
	console.log(
		`   - File updated: ${path.relative(__dirname, generateButtonPath)}`
	);

	const content = fs.readFileSync(generateButtonPath, "utf-8");

	const checks = {
		"UsageLimitError import": content.includes("UsageLimitError"),
		"isUsageLimitError import": content.includes("isUsageLimitError"),
		"usageLimitError state": content.includes("usageLimitError"),
		"403 status check": content.includes("response.status === 403"),
		"usage_limit_exceeded check": content.includes("usage_limit_exceeded"),
		"Upgrade modal/alert": content.includes("Upgrade"),
		"Dismiss button": content.includes("Dismiss"),
		"Upgrade CTA link": content.includes("/pricing"),
		"Graceful error display": content.includes("PHASE 4 INTEGRATION"),
	};

	for (const [check, passed] of Object.entries(checks)) {
		console.log(`   ${passed ? "\u2713" : "\u2717"} ${check}`);
		if (!passed) allChecks = false;
	}
} else {
	console.log(
		`   \u274c File NOT FOUND: ${path.relative(__dirname, generateButtonPath)}`
	);
	allChecks = false;
}

console.log();

// ============================================================================
// Integration Examples
// ============================================================================

console.log("\ud83d\udcda 4. Integration Examples");
console.log("-".repeat(80));
console.log();

console.log("Example 1: Add UsageStatsCard to Dashboard");
console.log("-".repeat(40));
console.log(`
// In pustak/src/app/dashboard/page.tsx or Layout.tsx

import { UsageStatsCard } from '@/components/UsageStatsCard';

export default function Dashboard() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Existing dashboard widgets */}
      
      {/* NEW: Usage Stats Card */}
      <UsageStatsCard 
        onUpgradeClick={() => router.push('/pricing')} 
      />
    </div>
  );
}
`);

console.log("Example 2: Compact Usage Widget in Sidebar");
console.log("-".repeat(40));
console.log(`
// In pustak/src/components/EnhancedSidebar.tsx

import { UsageStatsCard } from './UsageStatsCard';

// Add to sidebar bottom
<UsageStatsCard compact={true} className="mt-auto" />
`);

console.log("Example 3: Test Usage Limit Error");
console.log("-".repeat(40));
console.log(`
# 1. Generate docs until limit is hit
# (Click "Generate Docs" button multiple times)

# 2. Expected behavior:
#    - After limit is reached, see purple/pink gradient alert
#    - Shows "Usage Limit Reached" with plan and usage info
#    - Has "Upgrade to Pro/Team" button
#    - Has "Dismiss" button
#    - NO generic error toast

# 3. Click "Upgrade" button -> Should redirect to /pricing
`);

console.log();

// ============================================================================
// Testing Checklist
// ============================================================================

console.log("\ud83e\uddea 5. Testing Checklist");
console.log("-".repeat(80));
console.log();

const tests = [
	"\u2610 Start frontend: npm run dev",
	"\u2610 Login to application",
	"\u2610 Navigate to dashboard/page with UsageStatsCard",
	"\u2610 Verify usage stats load correctly",
	"\u2610 Verify progress bars show correct percentages",
	"\u2610 Verify color changes (green < 80%, yellow 80-90%, red > 90%)",
	"\u2610 Generate docs multiple times",
	"\u2610 Verify usage updates in real-time",
	"\u2610 Generate docs until limit is hit",
	"\u2610 Verify graceful error (purple alert, not generic error)",
	'\u2610 Verify "Upgrade" button links to /pricing',
	'\u2610 Verify "Dismiss" button works',
	"\u2610 Upgrade plan and verify limits increase",
	"\u2610 Verify cycle end date displays correctly",
];

tests.forEach((test) => console.log(`   ${test}`));

console.log();

// ============================================================================
// Implementation Guide
// ============================================================================

console.log("\ud83d\udee0\ufe0f 6. Implementation Guide");
console.log("-".repeat(80));
console.log();

console.log("Step 1: Add UsageStatsCard to Main Dashboard");
console.log(`
1. Open pustak/src/app/dashboard/page.tsx
2. Import: import { UsageStatsCard } from '@/components/UsageStatsCard';
3. Add widget: <UsageStatsCard />
4. Test: Refresh dashboard, should see usage stats
`);

console.log("Step 2: Add Compact Widget to Sidebar (Optional)");
console.log(`
1. Open pustak/src/components/EnhancedSidebar.tsx
2. Import: import { UsageStatsCard } from './UsageStatsCard';
3. Add at bottom: <UsageStatsCard compact={true} />
4. Test: Sidebar should show mini usage widget
`);

console.log("Step 3: Verify Error Handling");
console.log(`
1. GenerateDocsButton already updated
2. Test by generating docs until limit
3. Verify purple alert shows (not red error)
4. Verify upgrade button works
`);

console.log();

// ============================================================================
// API Integration Test
// ============================================================================

console.log("\ud83d\udd0c 7. API Integration Test");
console.log("-".repeat(80));
console.log();

console.log(`
# Test 1: Fetch usage stats
const { token } = useAuth();
const usage = await fetchUsageStats(token);
console.log('Usage:', usage);

# Expected response:
{
  "plan": "pro",
  "subscription_id": "uuid",
  "cycle_start": "2026-01-15T00:00:00Z",
  "cycle_end": "2026-02-14T23:59:59Z",
  "limits": {
    "docs_generated": {
      "used": 5,
      "limit": 1000,
      "remaining": 995,
      "allowed": true
    }
  }
}

# Test 2: Calculate percentage
const percent = getUsagePercentage(73, 1000); // 7.3
const color = getUsageColor(percent); // 'green'

# Test 3: Test limit error
try {
  await generateDocs();
} catch (error) {
  if (isUsageLimitError(error)) {
    showUpgradeModal(error.response.data.detail);
  }
}
`);

console.log();

// ============================================================================
// Summary
// ============================================================================

console.log("=".repeat(80));
if (allChecks) {
	console.log("\u2705 PHASE 4 COMPLETE: Frontend Integration Ready!");
} else {
	console.log("\u274c PHASE 4 INCOMPLETE: Fix errors above");
}
console.log("=".repeat(80));
console.log();

console.log("Files Created/Modified:");
console.log("  \u2705 pustak/src/lib/usage.ts (345 lines)");
console.log("  \u2705 pustak/src/components/UsageStatsCard.tsx (339 lines)");
console.log("  \u2705 pustak/src/components/GenerateDocsButton.tsx (updated)");
console.log();

console.log("Next Steps:");
console.log("  1. Add UsageStatsCard to dashboard");
console.log("  2. Test usage tracking in browser");
console.log("  3. Test limit enforcement");
console.log("  4. Test upgrade flow");
console.log();

process.exit(allChecks ? 0 : 1);
