/**
 * Test script for dual persona frontend routing
 * 
 * This script simulates different URL scenarios to test the persona-based routing:
 * 1. Default URL (should redirect to dev persona)
 * 2. Explicit dev persona URL
 * 3. Internal persona URL (should check auth)
 * 4. Invalid persona (should default to dev)
 */

const TEST_CASES = [
  {
    name: "Default URL (no persona)",
    url: "https://example.docbook.site/repo-name",
    expectedRedirect: "https://example.docbook.site/docs/example/repo-name/dev",
    description: "Should redirect to dev persona when no persona is specified"
  },
  {
    name: "Explicit dev persona URL",
    url: "https://example.docbook.site/repo-name/dev",
    expectedRedirect: null, // No redirect expected
    description: "Should load dev persona docs directly"
  },
  {
    name: "Internal persona URL (unauthenticated)",
    url: "https://example.docbook.site/repo-name/internal",
    expectedRedirect: "https://example.docbook.site/login?redirect=https://example.docbook.site/repo-name/internal",
    description: "Should redirect to login when accessing internal docs without auth"
  },
  {
    name: "Invalid persona",
    url: "https://example.docbook.site/repo-name/invalid-persona",
    expectedRedirect: "https://example.docbook.site/docs/example/repo-name/dev/invalid-persona",
    description: "Should treat invalid persona as part of the path and default to dev"
  },
  {
    name: "Nested path with dev persona",
    url: "https://example.docbook.site/repo-name/dev/some/nested/path",
    expectedRedirect: null, // No redirect expected
    description: "Should handle nested paths correctly with dev persona"
  },
  {
    name: "Nested path with internal persona",
    url: "https://example.docbook.site/repo-name/internal/some/nested/path",
    expectedRedirect: "https://example.docbook.site/login?redirect=https://example.docbook.site/repo-name/internal/some/nested/path",
    description: "Should redirect to login for nested paths with internal persona"
  }
];

// Simulate middleware behavior
function simulateMiddleware(url) {
  console.log(`\n🧪 Testing: ${url}`);
  
  // Parse URL
  const urlObj = new URL(url);
  const hostname = urlObj.hostname;
  const pathname = urlObj.pathname;
  
  // Extract org from subdomain
  const hostParts = hostname.split('.');
  const org = hostParts[0];
  
  console.log(`  📌 Org: ${org}`);
  
  // Parse path to extract repo and possibly persona
  const pathSegments = pathname.split('/').filter(Boolean);
  const repoName = pathSegments[0] || "";
  let personaName = pathSegments[1] || "";
  const remainingPath = pathSegments.slice(personaName ? 2 : 1).join('/');
  
  console.log(`  📌 Path segments: ${JSON.stringify(pathSegments)}`);
  console.log(`  📌 Repo: ${repoName}`);
  console.log(`  📌 Persona: ${personaName}`);
  console.log(`  📌 Remaining path: ${remainingPath}`);
  
  // Check if the second segment is a valid persona
  const validPersonas = ["internal", "dev"];
  let redirect = null;
  
  if (!validPersonas.includes(personaName)) {
    // If persona is not valid, it's part of the path
    console.log(`  ⚠️ Invalid persona "${personaName}", treating as path and defaulting to "dev"`);
    
    // Construct redirect URL - include the invalid persona as part of the path
    let pathWithInvalidPersona = personaName;
    if (remainingPath) {
      pathWithInvalidPersona += '/' + remainingPath;
    }
    
    personaName = "dev";
    const redirectPath = `/docs/${org}/${repoName}/${personaName}${pathWithInvalidPersona ? '/' + pathWithInvalidPersona : ''}`;
    redirect = `https://${hostname}${redirectPath}`;
  } else if (personaName === "internal") {
    // Check for auth when accessing internal persona
    const hasAuth = false; // Simulate no auth
    
    if (!hasAuth) {
      console.log(`  🔒 Unauthorized access to internal docs`);
      redirect = `https://${hostname}/login?redirect=${url}`;
    }
  } else if (!personaName) {
    // Default to dev persona if no persona specified
    console.log(`  ℹ️ No persona specified, defaulting to "dev"`);
    redirect = `https://${hostname}/docs/${org}/${repoName}/dev`;
  }
  
  return {
    org,
    repo: repoName,
    persona: personaName,
    path: remainingPath,
    redirect
  };
}

// Run tests
console.log("🚀 RUNNING DUAL PERSONA FRONTEND TESTS");
console.log("=====================================");

let passedTests = 0;
let failedTests = 0;

TEST_CASES.forEach((test, index) => {
  console.log(`\n📋 TEST ${index + 1}: ${test.name}`);
  console.log(`Description: ${test.description}`);
  
  const result = simulateMiddleware(test.url);
  
  // Check if redirect matches expected
  const redirectMatches = 
    (result.redirect === test.expectedRedirect) || 
    (result.redirect && test.expectedRedirect && result.redirect.includes(test.expectedRedirect));
  
  if (redirectMatches) {
    console.log(`✅ PASS: Redirect behavior correct`);
    if (result.redirect) {
      console.log(`  Expected redirect: ${test.expectedRedirect}`);
      console.log(`  Actual redirect: ${result.redirect}`);
    } else {
      console.log(`  No redirect expected or performed`);
    }
    passedTests++;
  } else {
    console.log(`❌ FAIL: Redirect behavior incorrect`);
    console.log(`  Expected redirect: ${test.expectedRedirect}`);
    console.log(`  Actual redirect: ${result.redirect}`);
    failedTests++;
  }
});

console.log("\n=====================================");
console.log(`🧮 TEST SUMMARY: ${passedTests} passed, ${failedTests} failed`);
if (failedTests === 0) {
  console.log("🎉 All tests passed!");
} else {
  console.log("⚠️ Some tests failed!");
}
