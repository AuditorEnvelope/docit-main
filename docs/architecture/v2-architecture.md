# Architecture v2

## System Overview
The high-level architecture of the DocAI system can be described as a microservices-based architecture, with the following components: Core, API, Database, and Frontend. The Core component serves as the central logic hub, responsible for processing and generating documentation content. The API component provides a RESTful interface for interacting with the system, while the Database component stores and manages the documentation data. The Frontend component, built using the Pustak application, is responsible for rendering the documentation content to the user.

The relationships between these components can be described as follows:
- The Core component interacts with the Database component to retrieve and store documentation data.
- The API component interacts with the Core component to process and generate documentation content.
- The Frontend component interacts with the API component to retrieve and display the documentation content.

The data flow within the system can be described as follows:
1. The user interacts with the Frontend component, sending a request to retrieve documentation content.
2. The Frontend component sends a request to the API component to retrieve the documentation content.
3. The API component sends a request to the Core component to process and generate the documentation content.
4. The Core component retrieves the necessary data from the Database component and processes it to generate the documentation content.
5. The Core component returns the generated documentation content to the API component.
6. The API component returns the documentation content to the Frontend component.
7. The Frontend component renders the documentation content to the user.

## Component Details
### Core
- Purpose: The Core component serves as the central logic hub, responsible for processing and generating documentation content.
- Responsibilities: The Core component is responsible for retrieving data from the Database component, processing it, and generating the documentation content.
- Interfaces: The Core component interacts with the Database component using a database interface, and with the API component using a RESTful API.
- Dependencies: The Core component depends on the Database component for data storage and retrieval, and on the API component for receiving requests and sending responses.

### API
- Purpose: The API component provides a RESTful interface for interacting with the system.
- Responsibilities: The API component is responsible for receiving requests from the Frontend component, sending requests to the Core component, and returning responses to the Frontend component.
- Interfaces: The API component interacts with the Frontend component using a RESTful API, and with the Core component using a RESTful API.
- Dependencies: The API component depends on the Core component for processing and generating documentation content, and on the Frontend component for receiving requests.

### Database
- Purpose: The Database component stores and manages the documentation data.
- Responsibilities: The Database component is responsible for storing and retrieving documentation data, and for providing it to the Core component upon request.
- Interfaces: The Database component interacts with the Core component using a database interface.
- Dependencies: The Database component depends on the Core component for data retrieval and storage requests.

### Frontend (Pustak)
- Purpose: The Frontend component, built using the Pustak application, is responsible for rendering the documentation content to the user.
- Responsibilities: The Frontend component is responsible for sending requests to the API component to retrieve documentation content, and for rendering the received content to the user.
- Interfaces: The Frontend component interacts with the API component using a RESTful API.
- Dependencies: The Frontend component depends on the API component for receiving documentation content, and on the user for sending requests.

## Technology Stack
- Languages and frameworks: The system uses Python (py) for the Core and API components, JavaScript (js) and TypeScript (ts) for the Frontend component.
- Databases and storage: The system uses a database (e.g., relational or NoSQL) for storing and managing documentation data.
- External services: The system uses external services such as GitHub and OpenAI for fetching and processing documentation data.
- Infrastructure: The system is deployed on a cloud-based infrastructure, with the Core and API components running on a server, and the Frontend component running on a client-side browser.

## Design Patterns
- Patterns used: The system uses the Model-View-Controller (MVC) pattern for the Frontend component, and the Repository Pattern for the Core component.
- Why they were chosen: The MVC pattern was chosen for the Frontend component because it provides a clear separation of concerns between the model, view, and controller, making it easier to maintain and update the code. The Repository Pattern was chosen for the Core component because it provides a layer of abstraction between the business logic and the data storage, making it easier to switch between different data storage solutions.

## Scalability & Performance
- How the system scales: The system is designed to scale horizontally, with multiple instances of the Core and API components running behind a load balancer. The Frontend component is designed to scale vertically, with the client-side browser handling the rendering of the documentation content.
- Performance considerations: The system is optimized for performance, with caching mechanisms in place to reduce the load on the Core and API components. The Database component is also optimized for performance, with indexing and query optimization techniques used to improve data retrieval times.

## Security Architecture
- Authentication/Authorization: The system uses JSON Web Tokens (JWT) for authentication and authorization, with the API component verifying the tokens on each request.
- Data protection: The system uses encryption mechanisms (e.g., SSL/TLS) to protect data in transit, and access control mechanisms (e.g., role-based access control) to protect data at rest.
- Security measures: The system uses security measures such as input validation, error handling, and logging to prevent and detect security breaches.

## Deployment Architecture
- Deployment model: The system is deployed using a cloud-based infrastructure, with the Core and API components running on a server, and the Frontend component running on a client-side browser.
- Infrastructure requirements: The system requires a server with a sufficient amount of CPU, memory, and storage to run the Core and API components, as well as a client-side browser with a sufficient amount of CPU, memory, and storage to run the Frontend component.

## Future Considerations
- Planned improvements: The system is planned to be improved with additional features such as advanced Markdown rendering, improved content presentation, and potential support for advanced Markdown features (e.g., syntax highlighting, tables).
- Known limitations: The system has known limitations such as the need for improved error handling, the need for additional security measures, and the need for improved performance optimization.