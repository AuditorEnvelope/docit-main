# Changelog


## [2025-10-21] - Implement full hierarchical caching for documentation generation

### Feature
- This commit introduces a comprehensive hierarchical caching mechanism for all structural node descriptions (repository, SDK, modules, features) within the documentation generation process. This significantly reduces the number of LLM calls required for incremental commits, drastically cutting down processing time and API costs.

### Details
- **Significance:** 8/10
- **Commit:** 3889ccc9577e459bdc454b2f28d892d5750c155c
- **Impact:** performance, cost_efficiency, developer_experience, build_pipeline_efficiency



## [2025-10-21] - Smart Caching for AI Descriptions: 10x Faster Incremental Updates

### Performance
- Implemented an intelligent caching mechanism for AI-generated file descriptions. This optimization reuses descriptions for unchanged files from previous commits, drastically reducing LLM calls, generation time, and operational costs for incremental updates, achieving up to 10x speed improvement for subsequent runs.

### Details
- **Significance:** 9/10
- **Commit:** 1043453929f32c228eab689304661e8e93817c01
- **Impact:** performance, cost_reduction, AI_pipeline_efficiency, developer_experience, scalability



## [2025-10-21] - Enhance documentation generation with AI-powered descriptions and metadata extraction

### Feature
- This commit introduces a major enhancement to the documentation generation process by integrating LLMs (Gemini, Groq, DeepSeek) to produce AI-generated descriptions for all code nodes (repo, SDK, module, feature, function, class). It also adds robust extraction of function parameters (including types and default values) and return types for both Python and TypeScript signatures. A graceful fallback mechanism ensures descriptions are always available, even if LLMs are temporarily inaccessible.

### Details
- **Significance:** 8/10
- **Commit:** 02648a103e721cbe7dce8705753b071e08edbc74
- **Impact:** documentation_generation, code_analysis, metadata_extraction, api_enrichment, LLM_integration



## [2025-10-21] - Fix Grouping in Hierarchical Doc Generator

### Bug_Fix
- Modified the hierarchical doc generator to group by directory structure instead of function prefix, improving document organization

### Details
- **Significance:** 8/10
- **Commit:** 93f2ebc515000fd90d045c1f9761a6dcb94527b2
- **Impact:** documentation, hierarchical_doc_generator



## [2025-10-21] - Introduce Recursive File Detection Depth Control for Doc Parsing

### Feature
- This commit introduces a new feature allowing control over the maximum recursion depth during hierarchical documentation parsing. Both the backend generation logic and the frontend display components are updated to support and utilize this depth limit, improving the structure and performance of documentation generation.

### Details
- **Significance:** 8/10
- **Commit:** b6ffa543e80f27d01571c5129c65d81f7ab8e6f8
- **Impact:** documentation_generation, frontend_display, cli_configuration



## [2025-10-21] - Fix for Hierarchical Document Generation/Storage Logic

### Bug_Fix
- Addresses a bug within the `hierarchical_doc_generator` module that impacts the correct structuring or storage of documents, ensuring proper hierarchical relationships.

### Details
- **Significance:** 7/10
- **Commit:** 7f17925591a50fba82d51e672c12eceb91195da3
- **Impact:** document_generation, data_integrity, document_structure_accuracy



## [2025-10-21] - Activate Automatic Hierarchical Documentation Generation

### Feature
- This change integrates and activates the `hierarchical_doc_generator` into the main application execution flow and file processing logic, ensuring hierarchical documentation is generated automatically.

### Details
- **Significance:** 8/10
- **Commit:** 049dd7d93a22436d2de938f39d21e883ce11209a
- **Impact:** internal_process, developer_experience, application_runtime



## [2025-10-15] - Efficiency Improvement

### Performance
- Implemented changes to increase efficiency in the system, affecting event consumer, LLM provider, and smart processor components

### Details
- **Significance:** 8/10
- **Commit:** 90a622deadc051928480ab22e8483a4a1648e382
- **Impact:** event_consumer, llm_provider, smart_processor



## [2025-10-15] - Improve LLM Prompts and Clean Up Codebase

### Bug_Fix
- Refined the Large Language Model (LLM) prompts within the comprehensive document generator to enhance output quality, accuracy, and clarity. Additionally, the codebase underwent a cleanup, and several obsolete development tracking and architecture documentation files were removed to streamline the repository.

### Details
- **Significance:** 8/10
- **Commit:** 111363f98d874e9484918921d4bb4dbaf9d82848
- **Impact:** LLM output quality, Code maintainability, Project documentation structure, Application core logic



## [2025-10-15] - Fix Tax Handling and API Response for Item Creation

### Bug_Fix
- This commit addresses potential issues with tax handling by adding validation to the `Item.tax` field, ensuring it's greater than zero. It also modifies the `POST /items/` endpoint to apply the tax to the item's price if provided and standardizes the API response format to include a success message.

### Details
- **Significance:** 7/10
- **Commit:** 3bb98f2770f2d8b65293500f63367adb1a69ed2b
- **Impact:** data_validation, api_behavior, business_logic



## [2025-10-15] - Fix Comprehensive Documentation Generator Reliability and Error Reporting

### Bug_Fix
- This commit addresses a critical bug in the comprehensive documentation generator that caused it to fail silently or produce incomplete/placeholder documentation. It also significantly enhances error logging by including full tracebacks in both the generator and the main execution script, improving system reliability and maintainability.

### Details
- **Significance:** 8/10
- **Commit:** 82d6b256b7bbf52e700e4ea0673ce360d72f7a68
- **Impact:** documentation_generation, error_handling, system_reliability, maintainability



## [2025-10-15] - Initial Implementation of Lekhak AI Service with Embeddings and RAG

### Feature
- This monumental commit introduces the core Lekhak AI service, establishing a robust architecture for contextual AI assistance in code. It integrates a commit bus for event processing, an indexing service leveraging a vector database (Milvus) for embeddings, and a RAG (Retrieval Augmented Generation) system to interact with various LLMs (Groq, OpenAI, Google Generative AI). This forms the foundational AI capabilities of the project.

### Details
- **Significance:** 9/10
- **Commit:** ea2bf9157afc4fd4ce9fc626701de39d105f6ba5
- **Impact:** core_ai_logic, data_processing, system_architecture, deployment, external_integrations, documentation



## [2025-10-12] - Refactor and Test Codebase

### Refactor
- Refactored codebase for improved maintainability, readability, and test coverage, including updates to documentation and API routes

### Details
- **Significance:** 8/10
- **Commit:** cb0c52f3d2f7fc22698a9f2d085b882d0991f804
- **Impact:** comprehensive_doc_generator, pustak, api, docs



## [2025-10-12] - Enhanced Rich Markdown Rendering in Pustak

### Feature
- Implemented enhanced Markdown rendering capabilities within the Pustak application, significantly improving the visual presentation, readability, and functionality of documentation content displayed to users.

### Details
- **Significance:** 8/10
- **Commit:** 103e459b233fb846d955fef06d7d3602c7b83024
- **Impact:** user_experience, frontend_rendering, content_display



## [2025-10-12] - Fix issues in comprehensive code and Markdown generation

### Bug_Fix
- This commit addresses bugs within the `comprehensive_doc_generator.py` script that affected both code and Markdown output generation. The fix aims to improve the accuracy and reliability of the generated content, as evidenced by updates to the generator script, its corresponding tests, and a bug fix report.

### Details
- **Significance:** 8/10
- **Commit:** ec9d42b08ebedf160c19ce7db9a789c7716ed705
- **Impact:** documentation_generation, code_generation_utility, tool_reliability, generated_content_quality



## [2025-10-12] - Integration of Vision Intelligence Capabilities

### Feature
- This commit introduces 'Vision Intelligence' to the Lekhak AI system, enabling it to process visual data (images) using an external LLAVA integration and generate comprehensive documentation based on visual understanding. This new capability is integrated into the core processing, documentation generation, and frontend display.

### Details
- **Significance:** 8/10
- **Commit:** 0f09e5e0f44f595d7c2bc0e8863ecc45c314cb05
- **Impact:** ai_core_logic, documentation_generation, frontend_presentation, external_service_integration



## [2025-10-12] - Fix Markdown Rendering Issue

### Bug_Fix
- Resolved markdown rendering problem by updating the MarkdownRenderer component and related API functionality

### Details
- **Significance:** 8/10
- **Commit:** a6eb74bb0d2dd7f41f9f74ceca6d7c17a4279e7c
- **Impact:** markdown_rendering, frontend, api



## [2025-10-12] - Integrate GitHub as a Documentation Source for Pustak

### Feature
- Implemented the capability for the Pustak application to fetch and display documentation directly from GitHub repositories, introducing dynamic routing and dedicated GitHub API interaction logic. This enables Pustak to serve as a comprehensive front-end for GitHub-hosted documentation.

### Details
- **Significance:** 8/10
- **Commit:** 6f4aa000b16c9add03efe474003dd2d7fa0363b7
- **Impact:** documentation_loading, external_integrations, frontend_routing, data_fetching, content_management



## [2025-10-12] - Major Refactor of Pustak Documentation Handling Logic

### Refactor
- This commit represents a significant refactoring of the 'Pustak' component, which appears to be a dedicated documentation viewing and browsing application built with Next.js (TypeScript/React). The refactor overhauls its internal logic, structure, and potentially its interaction with data sources, aiming to improve maintainability, functionality, and user experience for accessing repository documentation.

### Details
- **Significance:** 8/10
- **Commit:** 7e2d81e7595dab40e7301af2a7b9a2c8d9a9a5c4
- **Impact:** frontend_application, documentation_rendering, api_integration, developer_experience



## [2025-10-12] - Add Pustak documentation platform with DocAI integration

### Feature
- This commit introduces 'Pustak', a new, dedicated documentation platform built with Next.js, designed to render and manage documentation generated by the DocAI system. It includes new API endpoints for synchronization and webhooks, and integrates with the core `lekhak_ai` (DocAI) system via a new `pustak_integration.py` script to automate documentation publishing.

### Details
- **Significance:** 9/10
- **Commit:** 2044f79a907d3b53a993ef36c17fcb3ee5895369
- **Impact:** documentation_platform, frontend_application, api_endpoints, system_integration, deployment_process, user_interface



## [2025-10-11] - Enhanced Documentation Generation and Analysis Capabilities

### Feature
- Added smart processing for GitHub push events, comprehensive change analysis, and documentation creation. Introduced multi-provider LLM support for improved content generation.

### Details
- **Significance:** 9/10
- **Commit:** 094fbd6d09ce7a086a7256814dceb0165158c4d2
- **Impact:** documentation, analysis, github_integration, llm


All notable changes to this project will be documented in this file.

