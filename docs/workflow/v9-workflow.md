# Workflow v9: Development, Documentation, and Deployment

**VERSION:** v9
**REASON FOR NEW VERSION:** Major workflow change detected: Temporarily Disable Hierarchical Documentation Generation

This document outlines the workflow for developing, documenting, and deploying the DocAI system. It covers the core processes, from setting up the development environment to maintaining the deployed system. This version incorporates a significant performance optimization by temporarily disabling hierarchical documentation generation.

## Development Workflow

### Setup

1.  **Clone Repository:** Clone the DocAI repository to your local machine using Git.
    ```bash
    git clone <repository_url>
    ```

2.  **Install Dependencies:** Navigate to the repository directory and install the required dependencies using a package manager like pip.
    ```bash
    cd DocAI
    pip install -r requirements.txt
    ```

3.  **Configure Environment:** Configure the environment variables, API keys, and other settings required for development. This often involves creating a `.env` file or setting environment variables directly in your shell.  Specifically, ensure LLM API keys are properly configured.

### Development Process (with diagram)

```
[Start] --> [Create Branch] --> [Code] --> [Test] --> [PR (Pull Request)] --> [Review] --> [Merge] --> [End]
                                        |                    |
                                        v                    v
                                    [Failed?]        [Changes Requested?]
                                        |                    |
                                        Yes                 Yes
                                        |                    |
                                    [Fix Code] <-----------[Address Review Feedback]
                                        |
                                        No
                                        |
                                    [Continue]
```

1.  **Create Branch:** Create a new feature branch from the `main` branch for each new feature, bug fix, or improvement.
    ```bash
    git checkout -b feature/new-feature
    ```

2.  **Code:** Implement the changes required for the feature or fix.  Adhere to coding standards and best practices.

3.  **Test:** Write unit tests, integration tests, and end-to-end tests to ensure the changes are working correctly and do not introduce regressions. Run all tests locally before submitting a pull request.
    ```bash
    pytest
    ```

4.  **PR (Pull Request):**  Submit a pull request to the `main` branch with a clear description of the changes and the rationale behind them.  Include the relevant issue number in the pull request description.  Ensure all tests pass in the CI environment.

5.  **Review:**  Assign the pull request to one or more reviewers for code review.  Be responsive to reviewer feedback and address any issues raised.

6.  **Merge:** Once the pull request has been approved and all tests pass, merge it into the `main` branch.

### Code Review Process

*   **Review Guidelines:** Reviewers should focus on code quality, correctness, security, performance, and adherence to coding standards. Ensure that the code is well-documented and easy to understand. Check for potential edge cases and error handling.

*   **Approval Process:** A pull request requires approval from at least one reviewer before it can be merged.  Reviewers should leave detailed comments explaining any issues or suggestions for improvement.  The author of the pull request should address all comments before the pull request is approved.  Once approved and all tests pass, a designated maintainer will merge the pull request.

## Documentation Workflow (Important Change in v9)

**v9 Change:**  Hierarchical documentation generation has been temporarily disabled due to performance issues, excessive LLM calls, and cache problems.  This significantly reduces commit times and LLM usage.

### Documentation Generation (Simplified in v9)

1.  **Identify Documentation Needs:** Determine which parts of the code need to be documented or updated based on the recent changes.
2.  **Write Documentation:** Update docstrings in the code and update the `README.md` file.  Focus on clearly explaining the purpose, functionality, and usage of each function, class, and module.
3.  **Manual Review:**  Review the updated documentation to ensure it is accurate, complete, and easy to understand.
4.  **Submit PR:** Submit a pull request with the documentation changes.

**Note:** Hierarchical documentation generation is temporarily disabled. The related files are `src/hierarchical_doc_generator.py` and the disabling trigger is in `src/smart_processor.py`. The `asyncio.run(generate_hierarchical_docs(...))` call is commented out in `src/smart_processor.py`.  Debug logging has been added in `src/hierarchical_doc_generator.py` related to caching.

### Documentation Update Steps (for README.md)

1.  **Edit README.md:**  Open the `README.md` file in a text editor.
2.  **Update Content:** Add or modify sections to reflect the recent changes, including new features, bug fixes, and usage instructions.  Pay special attention to the changes introduced in version 9 regarding the disabled hierarchical documentation generation.
3.  **Preview Changes:** Preview the changes in a Markdown viewer to ensure the formatting is correct.
4.  **Commit and Push:** Commit the changes and push them to the repository.

### Changelog Creation

1.  **Create/Update CHANGELOG.md:** Create or update a `CHANGELOG.md` file in the root of the repository.
2.  **Add Release Notes:** Add release notes for the current version, summarizing the changes, bug fixes, and new features. Specifically, highlight the disabling of hierarchical documentation generation in v9 and the reasons behind it.
3.  **Follow a Standard Format:** Use a standard format for the changelog entries, such as:

    ```
    ## [v9] - <Date>

    ### Changed

    - Temporarily disabled hierarchical documentation generation due to performance and cost concerns.
    ```

4.  **Commit and Push:** Commit the changes and push them to the repository.

## Deployment Workflow

This workflow assumes a basic deployment process.  Specific steps will vary based on the target environment.

### Staging Deployment

1.  **Checkout `main`:** Ensure you are on the `main` branch.
2.  **Pull Latest Changes:** Pull the latest changes from the remote `main` branch.
    ```bash
    git checkout main
    git pull origin main
    ```
3.  **Build Application:** Build the application using the appropriate build tools.
4.  **Deploy to Staging:** Deploy the built application to the staging environment. This may involve copying files, running deployment scripts, or using a deployment tool.
5.  **Validation:** Validate the deployment by running smoke tests and integration tests in the staging environment. Check logs for errors.  Verify that all expected functionality is working correctly.

### Production Deployment

1.  **Checkout `main`:** Ensure you are on the `main` branch and have the latest changes.
2.  **Tag Release:** Create a tag for the release.
    ```bash
    git tag v9
    git push origin v9
    ```
3.  **Build Application:** Build the application using the appropriate build tools.  Ideally, this build should be automated by a CI/CD pipeline.
4.  **Deploy to Production:** Deploy the built application to the production environment.  This may involve a blue-green deployment, rolling update, or other deployment strategy to minimize downtime.
5.  **Validation:** Validate the deployment by running smoke tests and monitoring the application logs and metrics in the production environment.
6.  **Monitor:** Continuously monitor the application for errors and performance issues.

### Rollback Procedure

1.  **Identify Issue:** Identify the issue that requires a rollback.
2.  **Revert to Previous Version:** Deploy the previous version of the application to the production environment. This may involve restoring a backup or using a deployment tool to revert to the previous deployment.
3.  **Monitor:** Monitor the application after the rollback to ensure the issue is resolved.
4.  **Investigate:** Investigate the cause of the issue and fix it before deploying the next version.

## CI/CD Pipeline

(The analysis indicates no CI/CD currently exists.  A basic outline is provided assuming future implementation).

### Build Process

1.  **Trigger:** The CI/CD pipeline is triggered automatically on every commit to the `main` branch or when a pull request is created.
2.  **Checkout Code:** The pipeline checks out the code from the repository.
3.  **Install Dependencies:** The pipeline installs the required dependencies.
4.  **Build Application:** The pipeline builds the application.

### Testing Stages

1.  **Unit Tests:** The pipeline runs unit tests to verify the correctness of individual components.
2.  **Integration Tests:** The pipeline runs integration tests to verify the interaction between different components.
3.  **End-to-End Tests:** The pipeline runs end-to-end tests to verify the application as a whole.

### Deployment Stages

1.  **Staging Deployment:** The pipeline deploys the application to the staging environment.
2.  **Production Deployment:** The pipeline deploys the application to the production environment after successful staging deployment and approval.

## Release Process

### Version Management

*   **Semantic Versioning:** Use semantic versioning (MAJOR.MINOR.PATCH) to indicate the type of changes in each release.
*   **Tagging:** Tag each release in Git with the version number.

### Release Notes

*   **Changelog:** Create a changelog file that summarizes the changes in each release.
*   **Communication:** Communicate the release to users through release notes, blog posts, or other channels.

## Monitoring & Maintenance

### Health Checks

*   **Endpoints:** Implement health check endpoints that can be used to monitor the health of the application.
*   **Alerting:** Set up alerting based on health check results to notify operators of any issues.

### Logging

*   **Structured Logging:** Use structured logging to make it easier to analyze logs and identify issues.
*   **Log Aggregation:** Aggregate logs from all application components into a central location.

### Incident Response

*   **Playbooks:** Create playbooks for common incidents to guide operators through the resolution process.
*   **On-Call Rotation:** Establish an on-call rotation to ensure that someone is always available to respond to incidents.

## Common Tasks

### Task 1: Adding a New Feature

1.  Create a new branch for the feature.
2.  Implement the feature, writing tests as you go.
3.  Document the feature.
4.  Submit a pull request for review.
5.  Address reviewer feedback and merge the pull request.

### Task 2: Fixing a Bug

1.  Create a new branch for the bug fix.
2.  Reproduce the bug and write a test case that demonstrates the bug.
3.  Fix the bug.
4.  Run all tests to ensure the bug is fixed and no regressions have been introduced.
5.  Submit a pull request for review.
6.  Address reviewer feedback and merge the pull request.
