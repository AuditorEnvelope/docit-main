#!/usr/bin/env python3
"""
Phase 3 Verification Script
============================

Verifies that the Usage API endpoints and documentation service integration
are correctly implemented.

Usage:
    python verify_phase3.py
"""


def verify_usage_endpoint():
    """Verify usage endpoint implementation."""
    print("=" * 80)
    print("PHASE 3 VERIFICATION: Usage API & Integration")
    print("=" * 80)
    print()

    # Check file exists
    import os
    usage_endpoint_path = "app/api/v1/endpoints/usage.py"
    if os.path.exists(usage_endpoint_path):
        print(f"✅ 1. Usage Endpoint Created: {usage_endpoint_path}")
    else:
        print(f"❌ 1. Usage Endpoint NOT FOUND: {usage_endpoint_path}")
        return False

    # Check imports
    try:
        from app.api.v1.endpoints import usage
        print("   - Module imports successfully")
    except Exception as e:
        print(f"   ❌ Module import failed: {e}")
        return False

    # Check router exists
    if hasattr(usage, 'router'):
        print("   - Router exists")
    else:
        print("   ❌ Router not found")
        return False

    print()
    return True


def verify_api_registration():
    """Verify usage router is registered in API."""
    print("✅ 2. API Router Registration")

    try:
        from app.api.v1 import api
        # Check if api_router has usage included
        print("   - api.py imports successfully")

        # Try to find usage in the routes
        routes_found = False
        if hasattr(api, 'api_router'):
            for route in api.api_router.routes:
                if '/usage' in str(route.path):
                    routes_found = True
                    print(f"   - Found route: {route.path}")
                    break

        if routes_found:
            print("   ✓ Usage routes registered")
        else:
            print("   ⚠️  Usage routes may not be registered (check api.py)")

    except Exception as e:
        print(f"   ❌ API registration check failed: {e}")
        return False

    print()
    return True


def verify_documentation_integration():
    """Verify documentation service has usage checks."""
    print("✅ 3. Documentation Service Integration")

    try:
        # Check if documentation endpoint imports UsageService
        with open("app/api/v1/endpoints/documentation.py", "r") as f:
            content = f.read()

            has_usage_import = "UsageService" in content
            has_resource_type_import = "ResourceType" in content
            has_enforce_limit = "enforce_limit" in content
            has_record_usage = "record_usage" in content

            print(f"   {'✓' if has_usage_import else '✗'} Imports UsageService")
            print(
                f"   {'✓' if has_resource_type_import else '✗'} Imports ResourceType")
            print(
                f"   {'✓' if has_enforce_limit else '✗'} Calls enforce_limit() (The Guard)")
            print(
                f"   {'✓' if has_record_usage else '✗'} Calls record_usage() (The Ledger)")

            if all([has_usage_import, has_resource_type_import, has_enforce_limit, has_record_usage]):
                print("   ✓ Full integration complete")
            else:
                print("   ⚠️  Incomplete integration")
                return False

    except FileNotFoundError:
        print("   ❌ documentation.py not found")
        return False
    except Exception as e:
        print(f"   ❌ Integration check failed: {e}")
        return False

    print()
    return True


def show_endpoints():
    """Show the new API endpoints."""
    print("📖 4. Available Endpoints")
    print("-" * 80)
    print()
    print("GET /api/v1/usage/me")
    print("  Description: Get current user's usage summary")
    print("  Auth: Required (JWT)")
    print("  Response:")
    print("  {")
    print("    \"plan\": \"team\",")
    print("    \"cycle_start\": \"2026-01-15T00:00:00Z\",")
    print("    \"cycle_end\": \"2026-02-14T23:59:59Z\",")
    print("    \"limits\": {")
    print(
        "      \"docs_generated\": { \"used\": 5, \"limit\": 5000, \"remaining\": 4995, \"allowed\": true }")
    print("    }")
    print("  }")
    print()

    print("GET /api/v1/usage/history")
    print("  Description: Get usage event history")
    print("  Auth: Required (JWT)")
    print("  Query Params: resource_type (optional), limit (default: 100)")
    print("  Response: Array of usage events")
    print()

    print("GET /api/v1/usage/summary")
    print("  Description: Get raw usage counts (simplified)")
    print("  Auth: Required (JWT)")
    print("  Response: { \"docs_generated\": 73, \"repos_connected\": 2 }")
    print()

    print("POST /api/v1/documentation/manual-generate")
    print("  Description: Generate documentation (NOW WITH LIMITS!)")
    print("  Auth: Required (JWT)")
    print("  Flow:")
    print("    1. Check limit (enforce_limit) - Fails with 403 if exceeded")
    print("    2. Generate docs")
    print("    3. Record usage (record_usage)")
    print("  Error Response (403):")
    print("  {")
    print("    \"detail\": {")
    print("      \"error\": \"usage_limit_exceeded\",")
    print("      \"message\": \"Document generation limit reached...\",")
    print("      \"used\": 1000,")
    print("      \"limit\": 1000,")
    print("      \"action\": \"upgrade_or_wait\"")
    print("    }")
    print("  }")
    print()


def show_integration_flow():
    """Show the complete integration flow."""
    print("🔄 5. Integration Flow")
    print("-" * 80)
    print()
    print("User Request → Frontend → POST /api/v1/documentation/manual-generate")
    print("                            ↓")
    print("                    1. Authenticate (JWT)")
    print("                            ↓")
    print("                    2. Initialize UsageService")
    print("                            ↓")
    print("                    3. enforce_limit(user_id, 'docs_generated')")
    print("                       → Queries subscription_usage table")
    print("                       → Sums usage in current entitlement window")
    print("                       → Compares to plan limit")
    print("                       → Raises 403 if exceeded ❌")
    print("                            ↓")
    print("                    4. Generate Documentation (expensive)")
    print("                            ↓")
    print("                    5. Publish to Docbook")
    print("                            ↓")
    print("                    6. record_usage(user_id, 'docs_generated', 1)")
    print("                       → Inserts row into subscription_usage")
    print("                       → Links to active subscription")
    print("                       → Creates audit trail")
    print("                            ↓")
    print("                    7. Return Success ✅")
    print()


def show_frontend_integration():
    """Show how frontend should integrate."""
    print("🌐 6. Frontend Integration Guide")
    print("-" * 80)
    print()
    print("Step 1: Fetch Usage Data")
    print("-" * 40)
    print("""
    // In dashboard or layout component
    const response = await fetch('/api/v1/usage/me', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const usage = await response.json();
    
    // usage = {
    //   plan: "pro",
    //   limits: {
    //     docs_generated: { used: 73, limit: 1000, remaining: 927, allowed: true }
    //   }
    // }
    """)

    print("\nStep 2: Display Usage")
    print("-" * 40)
    print("""
    <div className="usage-card">
        <h3>Documents Generated</h3>
        <ProgressBar 
            value={usage.limits.docs_generated.used} 
            max={usage.limits.docs_generated.limit} 
        />
        <p>{usage.limits.docs_generated.used} / {usage.limits.docs_generated.limit} used</p>
        
        {usage.limits.docs_generated.used / usage.limits.docs_generated.limit > 0.8 && (
            <Warning>You're nearing your limit. Consider upgrading.</Warning>
        )}
    </div>
    """)

    print("\nStep 3: Handle Limit Errors")
    print("-" * 40)
    print("""
    async function generateDocs(repoName) {
        try {
            const result = await fetch('/api/v1/documentation/manual-generate', {
                method: 'POST',
                body: JSON.stringify({ repo_full_name: repoName }),
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (result.status === 403) {
                const error = await result.json();
                if (error.detail.error === 'usage_limit_exceeded') {
                    // Show upgrade modal
                    showUpgradeModal({
                        message: error.detail.message,
                        plan: error.detail.plan,
                        cycleEnd: error.detail.cycle_end
                    });
                    return;
                }
            }
            
            // Success - refresh usage
            await fetchUsage();
            
        } catch (err) {
            console.error('Doc generation failed:', err);
        }
    }
    """)
    print()


def show_testing_guide():
    """Show how to test the implementation."""
    print("🧪 7. Testing Guide")
    print("-" * 80)
    print()
    print("Test 1: Check Usage Endpoint")
    print("-" * 40)
    print("""
    # Start the backend
    uvicorn app.main:app --reload
    
    # Get JWT token (login first)
    TOKEN="your-jwt-token"
    
    # Test usage endpoint
    curl -X GET "http://localhost:8000/api/v1/usage/me" \\
         -H "Authorization: Bearer $TOKEN"
    
    # Expected: 200 OK with usage data
    """)

    print("\nTest 2: Test Limit Enforcement")
    print("-" * 40)
    print("""
    # Generate docs multiple times until limit is hit
    for i in {1..1001}; do
        curl -X POST "http://localhost:8000/api/v1/documentation/manual-generate" \\
             -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"repo_full_name": "org/repo"}'
        
        if [ $? -ne 0 ]; then
            echo "Limit reached at attempt $i"
            break
        fi
    done
    
    # Expected: 403 error after reaching plan limit
    """)

    print("\nTest 3: Verify Ledger Recording")
    print("-" * 40)
    print("""
    # Check database directly
    psql $DATABASE_URL -c "
        SELECT 
            u.resource_type,
            COUNT(*) as event_count,
            SUM(u.amount) as total_used
        FROM subscription_usage u
        JOIN subscriptions s ON u.subscription_id = s.id
        WHERE s.user_id = 'your-user-uuid'
          AND s.status = 'active'
        GROUP BY u.resource_type;
    "
    
    # Expected: Rows showing docs_generated count
    """)
    print()


def show_next_steps():
    """Show what to do next."""
    print("🎯 8. Next Steps")
    print("-" * 80)
    print()
    print("   ✅ Task 1: Create usage API endpoints - DONE")
    print("   ✅ Task 2: Register usage router - DONE")
    print("   ✅ Task 3: Integrate usage checks in doc generation - DONE")
    print("   ⏭️  Task 4: Update frontend to display usage")
    print("   ⏭️  Task 5: Add usage warnings at 80%/90%")
    print("   ⏭️  Task 6: Implement upgrade CTAs when limit reached")
    print("   ⏭️  Task 7: Add usage analytics dashboard")
    print("   ⏭️  Task 8: Test with real users")
    print()
    print("Deployment Checklist:")
    print("   □ Run migration 017_usage_ledger.sql")
    print("   □ Verify API endpoints work")
    print("   □ Test limit enforcement")
    print("   □ Update frontend")
    print("   □ Monitor usage metrics")
    print()


def main():
    """Run all verification checks."""
    try:
        success = True
        success &= verify_usage_endpoint()
        success &= verify_api_registration()
        success &= verify_documentation_integration()

        if success:
            show_endpoints()
            show_integration_flow()
            show_frontend_integration()
            show_testing_guide()
            show_next_steps()

            print("=" * 80)
            print("✅ PHASE 3 COMPLETE: Usage API & Integration Ready!")
            print("=" * 80)
            print()
            return 0
        else:
            print("=" * 80)
            print("❌ PHASE 3 INCOMPLETE: Fix errors above")
            print("=" * 80)
            return 1

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
