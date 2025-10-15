# Architecture v3
## System Overview
The Lekhak AI system is a microservice-oriented architecture designed to provide contextual AI assistance in code. The high-level architecture can be represented as follows:
```
+-------------------+      HTTP      +-------------------+
|     Frontend      |<-------------->|     API Gateway    |
+-------------------+                +-------------------+
                                             |
                                             | API Requests
                                             v
                                     +-------------------+
                                     |  Agent Service     |
                                     |  (Orchestrates AI  |
                                     |   tasks and events) |
                                     +-------------------+
                                             |
                                             | Event-driven
                                             |  Architecture
                                             v
                                     +-------------------+
                                     |  Commit Bus        |
                                     |  (Handles commit  |
                                     |   events and async  |
                                     |   processing)       |
                                     +-------------------+
                                             |
                                             | Event Consumption
                                             v
                                     +-------------------+
                                     |  Event Consumer    |
                                     |  (Processes commit |
                                     |   events and triggers|
                                     |   AI tasks)         |
                                     +-------------------+
                                             |
                                             | Data Processing
                                             v
                                     +-------------------+
                                     |  Universal Code    |
                                     |  Parser (Extracts   |
                                     |   information from  |
                                     |   codebases)        |
                                     +-------------------+
                                             |
                                             | Embeddings Generation
                                             v
                                     +-------------------+
                                     |  Indexer Service    |
                                     |  (Generates embeddings|
                                     |   using Sentence    |
                                     |   Transformers and  |
                                     |   stores in Milvus)  |
                                     +-------------------+
                                             |
                                             | RAG and LLM Integration
                                             v
                                     +-------------------+
                                     |  Lekhak AI Integration|
                                     |  (Orchestrates RAG  |
                                     |   and interactions   |
                                     |   with LLMs)         |
                                     +-------------------+
                                             |
                                             | Data Storage
                                             v
                                     +-------------------+
                                     |  Milvus (Vector     |
                                     |   Database for     |
                                     |   embeddings storage)|
                                     +-------------------+
                                             |
                                             | Overlay and Presentation
                                             v
                                     +-------------------+
                                     |  Overlay Service   |
                                     |  (Presents AI-generated|
                                     |   insights and results)|
                                     +-------------------+
```
The core components and their relationships are as follows:

*   Frontend: Handles user interactions and API requests.
*   API Gateway: Routes API requests to the Agent Service.
*   Agent Service: Orchestrates AI tasks and events.
*   Commit Bus: Handles commit events and async processing.
*   Event Consumer: Processes commit events and triggers AI tasks.
*   Universal Code Parser: Extracts information from codebases.
*   Indexer Service: Generates embeddings using Sentence Transformers and stores them in Milvus.
*   Lekhak AI Integration: Orchestrates RAG and interactions with LLMs.
*   Milvus: Stores embeddings and provides vector search capabilities.
*   Overlay Service: Presents AI-generated insights and results.

The data flow is as follows:

1.  The Frontend sends API requests to the API Gateway.
2.  The API Gateway routes the requests to the Agent Service.
3.  The Agent Service orchestrates AI tasks and events, triggering the Commit Bus.
4.  The Commit Bus handles commit events and async processing, triggering the Event Consumer.
5.  The Event Consumer processes commit events and triggers AI tasks, such as code parsing and embeddings generation.
6.  The Universal Code Parser extracts information from codebases.
7.  The Indexer Service generates embeddings using Sentence Transformers and stores them in Milvus.
8.  The Lekhak AI Integration orchestrates RAG and interactions with LLMs, retrieving relevant context from Milvus.
9.  The Overlay Service presents AI-generated insights and results.

## Component Details
### Agent Service
*   Purpose: Orchestrates AI tasks and events.
*   Responsibilities: Triggers the Commit Bus, interacts with the Lekhak AI Integration, and manages AI task execution.
*   Interfaces: API Gateway, Commit Bus, Lekhak AI Integration.
*   Dependencies: Commit Bus, Lekhak AI Integration.

### Commit Bus
*   Purpose: Handles commit events and async processing.
*   Responsibilities: Triggers the Event Consumer, manages commit event processing.
*   Interfaces: Agent Service, Event Consumer.
*   Dependencies: Event Consumer.

### Event Consumer
*   Purpose: Processes commit events and triggers AI tasks.
*   Responsibilities: Triggers code parsing, embeddings generation, and RAG.
*   Interfaces: Commit Bus, Universal Code Parser, Indexer Service, Lekhak AI Integration.
*   Dependencies: Universal Code Parser, Indexer Service, Lekhak AI Integration.

### Universal Code Parser
*   Purpose: Extracts information from codebases.
*   Responsibilities: Provides code metadata and context for AI tasks.
*   Interfaces: Event Consumer.
*   Dependencies: None.

### Indexer Service
*   Purpose: Generates embeddings using Sentence Transformers and stores them in Milvus.
*   Responsibilities: Creates and manages embeddings for code and documents.
*   Interfaces: Event Consumer, Milvus.
*   Dependencies: Milvus, Sentence Transformers.

### Lekhak AI Integration
*   Purpose: Orchestrates RAG and interactions with LLMs.
*   Responsibilities: Retrieves relevant context from Milvus, interacts with LLMs.
*   Interfaces: Event Consumer, Milvus, LLMs.
*   Dependencies: Milvus, LLMs.

### Milvus
*   Purpose: Stores embeddings and provides vector search capabilities.
*   Responsibilities: Manages embeddings storage and retrieval.
*   Interfaces: Indexer Service, Lekhak AI Integration.
*   Dependencies: None.

### Overlay Service
*   Purpose: Presents AI-generated insights and results.
*   Responsibilities: Provides a user interface for AI-generated content.
*   Interfaces: Lekhak AI Integration.
*   Dependencies: Lekhak AI Integration.

## Technology Stack
*   Languages and frameworks: Python, FastAPI, Uvicorn, PyJWT, PyGithub, python-dotenv, google-generativeai, groq, openai, requests, gitpython.
*   Databases and storage: Milvus (vector database), AsyncPG (relational database).
*   External services: OpenAI, Google Generative AI, Groq.
*   Infrastructure: Docker, Docker Compose.

## Design Patterns
*   Patterns used: Microservices, Event-driven Architecture, Repository Pattern.
*   Why they were chosen: Microservices allow for scalability and flexibility, event-driven architecture enables async processing and loose coupling, and the repository pattern provides a clear data access layer.

## Scalability & Performance
*   How the system scales: The system is designed to scale horizontally, with each microservice capable of being scaled independently.
*   Performance considerations: The system uses async processing and event-driven architecture to minimize blocking and maximize throughput.

## Security Architecture
*   Authentication/Authorization: The system uses PyJWT for authentication and authorization.
*   Data protection: The system uses encryption and secure storage for sensitive data.
*   Security measures: The system implements secure coding practices, regular security audits, and monitoring.

## Deployment Architecture
*   Deployment model: The system is deployed using Docker and Docker Compose.
*   Infrastructure requirements: The system requires a containerization platform, a relational database, and a vector database.

## Future Considerations
*   Planned improvements: Integration with additional LLMs, improved code parsing and embeddings generation, enhanced user interface.
*   Known limitations: The system is currently limited to a specific set of LLMs and may require additional development for broader language support.