# Multi-Organization Commit Bus Processing

**Type:** feature  
**Significance:** 9/10  
**Date:** 2025-10-26 12:01:13 UTC  
**Commit:** 72349d9eecf4c94bb5d1045fac9785eb0d3c5f58  
**Branch:** refs/heads/main  

## Summary
Implemented a major feature enabling the system to process and synchronize GitHub commit data for multiple registered organizations, moving beyond a single-user/single-org paradigm. This involves significant changes to event consumption, token retrieval, and repository synchronization logic.

## Impact Scope
multi_organization_support, data_synchronization, github_api_integration, token_management, event_processing

## Affected Components
src/core/event_consumer.py, src/utilities/github_sync.py, Database interactions (users, org_registrations tables), GitHub API calls

## Technical Details
The `EventConsumer` class has been heavily refactored to support multi-organization processing. The `get_github_token` method now fetches the `github_access_token` directly from the `users` table, simplifying token management and making the `token_id` parameter effectively unused. A new `get_orgs_with_activity` method was added to query `org_registrations` and discover all active organizations along with their associated user and token information. Another new method, `get_org_repositories`, was introduced to fetch an organization's repositories from the GitHub API (`/user/repos` endpoint with pagination). The `check_missed_commits` method was transformed into the core orchestrator, iterating through all discovered organizations, fetching their respective GitHub token and repositories, and then initiating the commit synchronization for each repository using the `github_sync` utility. The `sync_repo_commits` method in `src/utilities/github_sync.py` was updated to accept an `org_id` parameter, enabling it to process commits within the context of a specific organization.
