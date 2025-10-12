"use client";

import { Layout } from "@/components/Layout";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  Home,
  Architecture,
  GitBranch,
  Code,
  History,
  Clock,
  ArrowLeft,
  ExternalLink,
  Calendar,
  User,
  GitCommit,
} from "lucide-react";
import Link from "next/link";

interface RepoPageProps {
  params: {
    repoName: string;
    docType: string;
  };
}

// Mock data - in real app, this would come from an API
const mockRepoData = {
  "hivemind-poc": {
    name: "hivemind-poc",
    fullName: "AuditorEnvelope/hivemind-poc",
    description: "Hivemind POC - Distributed AI Agent System",
    lastUpdated: "2024-01-15T10:30:00Z",
    docs: {
      summary: `# Hivemind POC Documentation

## Overview
Hivemind POC is a distributed AI agent system designed to demonstrate collaborative intelligence across multiple agents.

## Key Features
- **Distributed Architecture**: Multiple agents working together
- **Real-time Communication**: WebSocket-based messaging
- **Scalable Design**: Horizontal scaling capabilities
- **AI Integration**: Advanced AI models integration

## Technology Stack
- **Backend**: Node.js, Express, Redis
- **Frontend**: React, TypeScript
- **AI**: OpenAI GPT, Anthropic Claude
- **Infrastructure**: Docker, Kubernetes

## Getting Started
\`\`\`bash
# Clone the repository
git clone https://github.com/AuditorEnvelope/hivemind-poc.git

# Install dependencies
npm install

# Start the development server
npm run dev
\`\`\`

## Architecture Overview
The system consists of multiple specialized agents that communicate through a central message bus.`,

      architecture: `# System Architecture

## High-Level Architecture
\`\`\`
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │   Admin Panel   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │       API Gateway          │
                    └─────────────┬──────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │      Message Bus           │
                    │        (Redis)             │
                    └─────────────┬──────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                       │                        │
┌───────▼───────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
│ Auth Agent    │    │ Processing Agent  │    │ Storage Agent     │
└───────────────┘    └───────────────────┘    └───────────────────┘
\`\`\`

## Component Details

### API Gateway
- Handles incoming requests
- Authentication and authorization
- Rate limiting and load balancing

### Message Bus
- Redis-based pub/sub system
- Ensures reliable message delivery
- Supports real-time communication

### Agents
Each agent is specialized for specific tasks:

#### Auth Agent
- User authentication
- Session management
- Permission handling

#### Processing Agent
- AI model integration
- Task processing
- Result aggregation

#### Storage Agent
- Data persistence
- File management
- Backup and recovery`,

      workflow: `# Development Workflow

## Git Flow Strategy
We use Git Flow for our branching strategy:

### Branch Types
- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: New features
- **hotfix/***: Critical bug fixes
- **release/***: Release preparation

## Development Process

### 1. Feature Development
\`\`\`bash
# Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
\`\`\`

### 2. Code Review Process
- All changes require peer review
- Automated tests must pass
- Code coverage requirements
- Security scan approval

### 3. Deployment Pipeline
\`\`\`yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to staging
        run: |
          docker build -t hivemind-poc .
          docker push registry/hivemind-poc:latest
\`\`\`

## Quality Assurance

### Testing Strategy
- **Unit Tests**: 90% coverage minimum
- **Integration Tests**: API endpoints
- **E2E Tests**: Critical user flows
- **Performance Tests**: Load testing

### Code Standards
- ESLint configuration
- Prettier formatting
- TypeScript strict mode
- Conventional commits`,

      api: `# API Documentation

## Base URL
\`\`\`
Production: https://api.hivemind-poc.com/v1
Staging: https://staging-api.hivemind-poc.com/v1
\`\`\`

## Authentication
All API requests require authentication using JWT tokens.

\`\`\`bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     https://api.hivemind-poc.com/v1/agents
\`\`\`

## Endpoints

### Agents

#### List Agents
\`\`\`http
GET /agents
\`\`\`

**Response:**
\`\`\`json
{
  "agents": [
    {
      "id": "agent-123",
      "name": "Auth Agent",
      "status": "active",
      "capabilities": ["authentication", "authorization"],
      "lastSeen": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10
}
\`\`\`

#### Create Agent
\`\`\`http
POST /agents
\`\`\`

**Request Body:**
\`\`\`json
{
  "name": "New Agent",
  "type": "processing",
  "config": {
    "maxConcurrentTasks": 5,
    "timeout": 30000
  }
}
\`\`\`

### Tasks

#### Submit Task
\`\`\`http
POST /tasks
\`\`\`

**Request Body:**
\`\`\`json
{
  "agentId": "agent-123",
  "type": "data_processing",
  "payload": {
    "data": "sample data",
    "options": {
      "priority": "high"
    }
  }
}
\`\`\`

## Error Handling

### Error Response Format
\`\`\`json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": {
      "field": "agentId",
      "reason": "Agent not found"
    }
  }
}
\`\`\`

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **500**: Internal Server Error`,

      changes: `# Recent Changes

## 2024-01-15 - Authentication System Update

### 🔐 Added OAuth2 Integration
- Implemented OAuth2 authentication flow
- Added JWT token management
- Enhanced security middleware

**Files Changed:**
- \`auth/oauth2.js\`
- \`middleware/auth.js\`
- \`config/auth.js\`

**Impact:** High - All API endpoints now require proper authentication

---

## 2024-01-14 - Performance Improvements

### ⚡ Database Optimization
- Added database connection pooling
- Implemented query caching
- Optimized slow queries

**Files Changed:**
- \`database/connection.js\`
- \`models/user.js\`
- \`utils/cache.js\`

**Impact:** Medium - Improved response times by 40%

---

## 2024-01-13 - Bug Fixes

### 🐛 Fixed Memory Leaks
- Resolved WebSocket connection leaks
- Fixed event listener cleanup
- Improved garbage collection

**Files Changed:**
- \`websocket/manager.js\`
- \`agents/base.js\`

**Impact:** High - Resolved critical memory issues

---

## 2024-01-12 - New Features

### ✨ Agent Health Monitoring
- Added health check endpoints
- Implemented monitoring dashboard
- Created alerting system

**Files Changed:**
- \`monitoring/health.js\`
- \`dashboard/components/HealthPanel.jsx\`

**Impact:** Low - Added monitoring capabilities`,

      changelog: `# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2024-01-15

### Added
- OAuth2 authentication system
- JWT token management
- Enhanced security middleware
- Agent health monitoring
- Performance monitoring dashboard

### Changed
- Updated API authentication flow
- Improved error handling
- Enhanced logging system

### Fixed
- Memory leak in WebSocket connections
- Database connection issues
- Authentication token expiration

## [2.0.0] - 2024-01-10

### Added
- Distributed agent architecture
- Real-time communication system
- Redis message bus integration
- Docker containerization
- Kubernetes deployment configs

### Changed
- Complete rewrite of core system
- New API structure
- Updated documentation

### Removed
- Legacy authentication system
- Old message queue implementation

## [1.5.0] - 2023-12-20

### Added
- Basic agent system
- Simple message passing
- REST API endpoints

### Changed
- Improved error handling
- Better logging

## [1.0.0] - 2023-12-01

### Added
- Initial project structure
- Basic documentation
- Core functionality`,
    },
  },
  "doc-ai": {
    name: "doc-ai",
    fullName: "AuditorEnvelope/doc-ai",
    description: "DocAI - Intelligent Documentation Agent",
    lastUpdated: "2024-01-15T09:15:00Z",
    docs: {
      summary: `# DocAI Documentation

## Overview
DocAI is an intelligent documentation agent that automatically generates and maintains documentation for software projects.

## Key Features
- **Multi-Provider LLM Support**: Gemini, Groq, DeepSeek
- **Smart Change Detection**: Only documents significant changes
- **GitBook Integration**: Seamless documentation publishing
- **Multi-Repository Support**: Scale across your organization

## Architecture
DocAI consists of several components working together to provide intelligent documentation generation.`,
      architecture: `# DocAI Architecture

## System Components

### Webhook Handler
- Receives GitHub webhook events
- Validates webhook signatures
- Processes push events

### Smart Processor
- Analyzes code changes
- Determines significance
- Generates documentation

### LLM Provider
- Multi-provider support
- Automatic failover
- Rate limit handling`,
      workflow: `# DocAI Workflow

## Change Detection Process
1. GitHub webhook triggers
2. Clone repository
3. Analyze changes
4. Generate documentation
5. Commit and push`,
      api: `# DocAI API

## Webhook Endpoint
\`\`\`
POST /webhook
\`\`\`

## Health Check
\`\`\`
GET /
\`\`\``,
      changes: `# DocAI Changes

## Recent Updates
- Added multi-provider LLM support
- Implemented smart change detection
- Created Pustak documentation platform`,
      changelog: `# DocAI Changelog

## [1.0.0] - 2024-01-15
- Initial release
- Multi-provider LLM support
- Smart documentation generation`,
    },
  },
};

export default function RepoPage({ params }: RepoPageProps) {
  const { repoName, docType } = params;
  const repoData = mockRepoData[repoName as keyof typeof mockRepoData];

  if (!repoData) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Repository Not Found
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              The repository "{repoName}" could not be found.
            </p>
            <Link
              href="/"
              className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  const docContent = repoData.docs[docType as keyof typeof repoData.docs];

  if (!docContent) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Document Not Found
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              The document "{docType}" could not be found for repository "
              {repoName}".
            </p>
            <Link
              href="/"
              className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  const getDocIcon = (type: string) => {
    switch (type) {
      case "summary":
        return <Home className="w-5 h-5" />;
      case "architecture":
        return <Architecture className="w-5 h-5" />;
      case "workflow":
        return <GitBranch className="w-5 h-5" />;
      case "api":
        return <Code className="w-5 h-5" />;
      case "changes":
        return <History className="w-5 h-5" />;
      case "changelog":
        return <Clock className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  const getDocTitle = (type: string) => {
    switch (type) {
      case "summary":
        return "Summary";
      case "architecture":
        return "Architecture";
      case "workflow":
        return "Workflow";
      case "api":
        return "API Documentation";
      case "changes":
        return "Recent Changes";
      case "changelog":
        return "Changelog";
      default:
        return type;
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-6xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Link
                  href="/"
                  className="flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back</span>
                </Link>

                <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />

                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    {getDocIcon(docType)}
                    <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                      {getDocTitle(docType)}
                    </h1>
                  </div>

                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {repoData.name}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>
                    Updated{" "}
                    {new Date(repoData.lastUpdated).toLocaleDateString()}
                  </span>
                </div>

                <a
                  href={`https://github.com/${repoData.fullName}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>View on GitHub</span>
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="p-8">
              <MarkdownRenderer content={docContent} />
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
