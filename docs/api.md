# API Documentation

*Updated: 2025-10-12*

This documentation details the new API capabilities introduced by the "Integrate GitHub as a Documentation Source for Pustak" feature. Pustak can now fetch, process, and display documentation directly from public GitHub repositories, acting as a unified front-end for various documentation sources.

---

## Pustak GitHub Documentation Integration API

### Version
`v1.0`

### Introduction

This new feature significantly enhances Pustak's ability to serve as a comprehensive documentation platform by integrating directly with GitHub. Users can now view documentation (such as `README.md` files, API documentation, or any other markdown files) hosted in public GitHub repositories directly through Pustak's interface.

This integration introduces:
*   A new dynamic frontend route for displaying GitHub-sourced content.
*   An underlying internal backend API that handles the fetching, processing, and rendering of content from GitHub. This backend API is designed for Pustak's internal use but is documented here for clarity on data flow and potential future external integrations.

### Base URLs

*   **Pustak Application Frontend:** `https://pustak.example.com` (replace with your Pustak deployment URL)
*   **Pustak Internal API:** `https://pustak.example.com/api/v1` (replace with your Pustak API deployment URL)

### Authentication

**For the Pustak Application Frontend (`/repo/{owner}/{repoName}/{docType}`):**
*   No explicit API key or token is required by the end-user. Access is based on Pustak's user session and permissions.
*   Pustak handles all internal GitHub API authentication (e.g., using a GitHub Personal Access Token or OAuth App credentials configured server-side) to fetch repository content.

**For the Pustak Internal API (`/api/v1/github-docs/...`):**
*   **Pustak API Key (Recommended for external consumers, or internal service-to-service calls):**
    *   Requests to this internal API (if exposed for other Pustak services or trusted third-party integrations) should include a valid Pustak API Key in the `Authorization` header.
    *   **Header:** `Authorization: Bearer <YOUR_PUSTAK_API_KEY>`
*   **GitHub Token (Not directly exposed):** Pustak's backend uses its own configured GitHub token(s) to interact with the GitHub API. This token is not exposed or required from the client side.

### Endpoints

This feature primarily exposes one new user-facing frontend route and one new internal backend API endpoint.

---

### 1. Frontend Route: Display GitHub Repository Documentation

This is the primary user-facing entry point for viewing GitHub-hosted documentation within the Pustak application. It renders the fetched and processed documentation content as a web page.

*   **Method:** `GET`
*   **Path:** `/repo/{owner}/{repoName}/{docType}`
*   **Description:** Renders a documentation page sourced directly from a specified GitHub repository. The content is fetched via Pustak's internal GitHub integration, processed (e.g., Markdown to HTML), and displayed.

#### Path Parameters

| Parameter | Type   | Description                                                                                                                                                                                                                                                                       | Example                    |
| :-------- | :----- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------- |
| `owner`   | `string` | The GitHub username or organization name that owns the repository.                                                                                                                                                                                                                | `auditor-envelope`         |
| `repoName`| `string` | The name of the GitHub repository.                                                                                                                                                                                                                                                | `lekhak_ai`                |
| `docType` | `string` | A logical type of document to fetch. Pustak maps these to specific files or default behaviors. <br>**Supported values:** <br>- `readme`: Fetches the `README.md` (or `readme.md`, `README`) file from the repository root. <br>- `api`: (Planned/Future) May map to `API.md`, `openapi.yaml`, or other designated API documentation. <br>- `file`: Requires the `filePath` query parameter to specify any arbitrary file. | `readme`, `api`, `file` |

#### Query Parameters

| Parameter  | Type     | Description                                                                                             | Default   |
| :--------- | :------- | :------------------------------------------------------------------------------------------------------ | :-------- |
| `branch`   | `string` | The branch of the repository to fetch documentation from.                                               | `main` or `master` (as per repo default) |
| `filePath` | `string` | **Required if `docType` is `file`**. The relative path to the documentation file within the repository (e.g., `docs/getting-started.md`). Ignored if `docType` is `readme` or `api`. | N/A       |

#### Example Request URL

*   `https://pustak.example.com/repo/auditor-envelope/lekhak_ai/readme`
*   `https://pustak.example.com/repo/auditor-envelope/lekhak_ai/readme?branch=dev`
*   `https://pustak.example.com/repo/octocat/Spoon-Knife/file?filePath=CONTRIBUTING.md`

#### Response

*   **Content-Type:** `text/html`
*   **Body:** The rendered HTML content of the documentation, integrated into the Pustak application's layout.
*   **Status Codes:**
    *   `200 OK`: Documentation successfully fetched and rendered.
    *   `400 Bad Request`: Missing or invalid path/query parameters.
    *   `404 Not Found`: Repository not found on GitHub, or specified `docType`/`filePath` not found within the repository.
    *   `500 Internal Server Error`: An error occurred on Pustak's server while fetching, processing, or rendering the documentation (e.g., GitHub API rate limit, Pustak processing error).

---

### 2. Internal API Endpoint: Fetch Raw GitHub Documentation Content

This endpoint is part of Pustak's internal API, designed to be called by Pustak's frontend or server-side components to fetch, process, and return documentation content as structured JSON. While primarily internal, it defines the data contract for the GitHub integration.

*   **Method:** `GET`
*   **Path:** `/api/v1/github-docs/{owner}/{repoName}/{docType}`
*   **Description:** Fetches, processes, and returns documentation content (Markdown, HTML, and metadata) from a specified public GitHub repository in JSON format.

#### Path Parameters

| Parameter | Type   | Description                                                                                                                                                                                                                                                                       | Example                    |
| :-------- | :----- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------- |
| `owner`   | `string` | The GitHub username or organization name that owns the repository.                                                                                                                                                                                                                | `auditor-envelope`         |
| `repoName`| `string` | The name of the GitHub repository.                                                                                                                                                                                                                                                | `lekhak_ai`                |
| `docType` | `string` | A logical type of document to fetch. Pustak maps these to specific files or default behaviors. <br>**Supported values:** <br>- `readme`: Fetches the `README.md` (or `readme.md`, `README`) file from the repository root. <br>- `api`: (Planned/Future) May map to `API.md`, `openapi.yaml`, or other designated API documentation. <br>- `file`: Requires the `filePath` query parameter to specify any arbitrary file. | `readme`, `api`, `file` |

#### Query Parameters

| Parameter  | Type     | Description                                                                                             | Default   |
| :--------- | :------- | :------------------------------------------------------------------------------------------------------ | :-------- |
| `branch`   | `string` | The branch of the repository to fetch documentation from.                                               | `main` or `master` (as per repo default) |
| `filePath` | `string` | **Required if `docType` is `file`**. The relative path to the documentation file within the repository (e.g., `docs/getting-started.md`). Ignored if `docType` is `readme` or `api`. | N/A       |

#### Request Headers

| Header        | Value                      | Description                                                  |
| :------------ | :------------------------- | :----------------------------------------------------------- |
| `Accept`      | `application/json`         | Specifies the expected response format.                      |
| `Authorization`| `Bearer <YOUR_PUSTAK_API_KEY>` | (Optional, but recommended if API is exposed) Pustak API key for authentication. |

#### Example Request URL

*   `https://pustak.example.com/api/v1/github-docs/auditor-envelope/lekhak_ai/readme`
*   `https://pustak.example.com/api/v1/github-docs/auditor-envelope/lekhak_ai/file?filePath=docs/faq.md&branch=v1.0`

#### Example Request (using `curl`)

```bash
curl -X GET \
  "https://pustak.example.com/api/v1/github-docs/auditor-envelope/lekhak_ai/readme?branch=main" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_PUSTAK_API_KEY"
```

#### Response

*   **Content-Type:** `application/json`
*   **Status Codes:**
    *   `200 OK`: Documentation successfully fetched and processed.
    *   `400 Bad Request`: Missing or invalid path/query parameters.
    *   `401 Unauthorized`: Pustak API Key is missing or invalid.
    *   `403 Forbidden`: Pustak's GitHub integration hit a rate limit or has insufficient permissions for the resource (less likely for public repos).
    *   `404 Not Found`: Repository not found on GitHub, or specified `docType`/`filePath` not found within the repository.
    *   `500 Internal Server Error`: An unexpected error occurred on Pustak's server (e.g., GitHub API issue, markdown processing failure).

#### Example Success Response (Status: `200 OK`)

```json
{
  "owner": "auditor-envelope",
  "repoName": "lekhak_ai",
  "docType": "readme",
  "branch": "main",
  "filePath": "README.md",
  "title": "Lekhak AI - A README",
  "markdownContent": "# Lekhak AI\n\nLekhak AI is an advanced documentation generation tool...\n\n## Features\n- Feature A\n- Feature B\n\n[More info](https://example.com/more-info)",
  "htmlContent": "<h1>Lekhak AI</h1>\n<p>Lekhak AI is an advanced documentation generation tool...</p>\n<h2>Features</h2>\n<ul>\n<li>Feature A</li>\n<li>Feature B</li>\n</ul>\n<p><a href=\"https://example.com/more-info\">More info</a></p>",
  "sourceUrl": "https://github.com/auditor-envelope/lekhak_ai/blob/main/README.md",
  "lastCommitSha": "a1b2c3d4e5f6...",
  "lastModified": "2023-10-27T10:30:00Z",
  "generatedAt": "2023-10-27T10:35:15Z"
}
```

### Error Handling

Pustak's API employs standard HTTP status codes for error reporting. The response body for error cases will typically be in JSON format, providing more details about the error.

| Status Code | Error Type            | Description                                                                                                                                  | Example Error Response                                                                                                                                                                                |
| :---------- | :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `400 Bad Request` | `InvalidParameters`   | The request was malformed, or required path/query parameters were missing or invalid.                                                        | `{"error": "InvalidParameters", "message": "Missing required 'filePath' query parameter for docType 'file'."}`                                                                                         |
| `401 Unauthorized`| `AuthenticationFailed`| The provided Pustak API Key is missing or invalid.                                                                                           | `{"error": "AuthenticationFailed", "message": "Invalid or missing Authorization header."}`                                                                                                          |
| `403 Forbidden`   | `AccessDenied`        | Pustak's internal GitHub integration encountered a rate limit, or the GitHub repository/file requires authentication that Pustak does not have (e.g., private repo). | `{"error": "AccessDenied", "message": "GitHub API rate limit exceeded. Please try again later."}` or `{"error": "AccessDenied", "message": "Access to private repository denied."}` |
| `404 Not Found`   | `ResourceNotFound`    | The specified GitHub repository, branch, or documentation file (`docType`/`filePath`) could not be found.                                    | `{"error": "ResourceNotFound", "message": "Repository 'non-existent-repo' not found for owner 'auditor-envelope'."}` or `{"error": "ResourceNotFound", "message": "File 'docs/nonexistent.md' not found."}` |
| `500 Internal Server Error`| `InternalServerError` | An unexpected error occurred on Pustak's server (e.g., internal processing failure, GitHub API downtime, unexpected data format).       | `{"error": "InternalServerError", "message": "An unexpected error occurred while processing the request. Please try again."}`                                                                     |

---

### Usage Examples

#### 1. Displaying a README from a GitHub Repo (Frontend)

To view the `README.md` of the `auditor-envelope/lekhak_ai` repository:

```
https://pustak.example.com/repo/auditor-envelope/lekhak_ai/readme
```

#### 2. Displaying a specific file from a GitHub Repo (Frontend)

To view a `CONTRIBUTING.md` file from `octocat/Spoon-Knife` on the `develop` branch:

```
https://pustak.example.com/repo/octocat/Spoon-Knife/file?filePath=CONTRIBUTING.md&branch=develop
```

#### 3. Programmatically Fetching README Content (Internal API)

To get the raw JSON content of the `README.md` from `auditor-envelope/lekhak_ai` for a different branch:

```bash
curl -X GET \
  "https://pustak.example.com/api/v1/github-docs/auditor-envelope/lekhak_ai/readme?branch=feature/new-docs" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_PUSTAK_API_KEY"
```

#### 4. Programmatically Fetching a specific documentation file (Internal API)

To get the HTML and Markdown content of `docs/getting-started.md` from `my-org/my-project`:

```bash
curl -X GET \
  "https://pustak.example.com/api/v1/github-docs/my-org/my-project/file?filePath=docs/getting-started.md" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_PUSTAK_API_KEY"
```

---

### Future Enhancements

*   **Webhook Integration:** Support for GitHub webhooks to automatically trigger documentation updates in Pustak when changes are pushed to a repository.
*   **Private Repository Support:** Allow integration with private GitHub repositories (requiring enhanced authentication configuration within Pustak).
*   **Version/Tag Selection:** Provide options to view documentation for specific Git tags or releases.
*   **Advanced `docType` Mapping:** Expand `docType` options to automatically identify and load `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, or specific API specification files (e.g., OpenAPI/Swagger JSON/YAML).
*   **Content Caching:** Implement more aggressive caching strategies for GitHub-sourced content to improve performance and reduce GitHub API calls.
*   **Link Rewriting:** Smarter handling of relative links within Markdown content to ensure they resolve correctly within Pustak's routing context.

---

### Contact

For any questions, issues, or feedback regarding this API, please contact the Pustak development team.