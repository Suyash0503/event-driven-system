# Event-Driven System with AI Agent Orchestration

## Overview

This project demonstrates the evolution of a traditional event-driven microservices architecture into an AI-powered multi-agent system. The application follows the Strangler Fig Pattern to incrementally migrate services while maintaining system availability and scalability.

The platform processes user and order events asynchronously using Apache Kafka, with AI agents orchestrating business workflows through Natural Language Processing (NLP) and OpenAI APIs.

---

## Features

- Event-driven microservices architecture
- Apache Kafka for asynchronous messaging
- Incremental migration using the Strangler Fig Pattern
- API Gateway for intelligent traffic routing
- AI-powered User Agent and Order Agent
- Orchestrator Service for workflow coordination
- Natural Language Processing for order placement
- OpenAI API integration for intelligent decision making
- MongoDB for persistent storage
- Docker Compose deployment
- REST APIs using FastAPI

---

## System Architecture

```
                Client
                   │
            API Gateway
                   │
      ┌────────────┴────────────┐
      │                         │
 Legacy Services         AI Orchestrator
      │                         │
      └──────────Kafka──────────┘
                   │
      ┌────────────┴────────────┐
      │                         │
 User Agent              Order Agent
      │                         │
 MongoDB                 MongoDB
```

---

## Technology Stack

- Python
- FastAPI
- Apache Kafka
- MongoDB
- Docker
- OpenAI API
- REST APIs
- Microservices
- Event-Driven Architecture

---

## Project Structure

```
api_gateway/
orchestrator_service/
order_agent/
user_agent/
order_service/
user_service_v1/
user_service_v2/
docker-compose.yml
gateway_config.json
```

---

## Workflow

1. Client submits a request.
2. API Gateway routes traffic between legacy and AI services.
3. Kafka publishes events.
4. AI Orchestrator coordinates business workflows.
5. User and Order Agents process requests.
6. OpenAI analyzes natural language input.
7. Services update MongoDB.
8. Final response is returned to the client.

---

## Running the Project

### Clone Repository

```bash
git clone https://github.com/Suyash0503/event-driven-system.git
cd event-driven-system
```

### Start Services

```bash
docker-compose up --build
```

### Start API Gateway

```bash
uvicorn api_gateway.main:app --reload
```

### Start Orchestrator

```bash
uvicorn orchestrator_service.main:app --reload
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| POST /user | Create user |
| POST /order | Place order |
| POST /task | AI Agent Task |
| POST /chat | Natural language order placement |

---

## Key Concepts

- Event-Driven Architecture
- Apache Kafka
- Strangler Fig Pattern
- AI Agents
- Workflow Orchestration
- REST APIs
- Distributed Systems
- NLP-powered Order Processing
- Incremental Migration
- Traffic Routing

---

## Future Enhancements

- Kubernetes deployment
- LangGraph integration
- Multi-agent collaboration
- Retrieval-Augmented Generation (RAG)
- Observability with OpenTelemetry
- CI/CD pipeline using GitHub Actions

---

## Author

**Suyash Sharma**

- LinkedIn: https://www.linkedin.com/in/ssyash
- GitHub: https://github.com/Suyash0503
