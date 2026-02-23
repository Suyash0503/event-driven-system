A Poly-Phase Evolution from Event-Driven Microservices to an Agent-Oriented Distributed System
Abstract

This repository presents the design, implementation, and architectural evolution of a cloud-ready event-driven microservices system extended into an agent-oriented distributed coordination model. The project demonstrates a structured transformation from traditional REST-based microservices toward a goal-driven, orchestrated multi-agent architecture. The system leverages asynchronous messaging, containerization, and orchestration patterns to explore trade-offs between modularity, reliability, coordination overhead, and architectural complexity.

1. Introduction

Modern distributed systems increasingly rely on microservices for scalability and modularity. However, as systems grow, coordination logic becomes fragmented across services, leading to tight coupling, coordination overhead, and limited flexibility in workflow management.

This project investigates the following research question:

Can an event-driven microservices architecture be systematically evolved into an agent-oriented orchestration model while preserving scalability and fault isolation?

The repository provides both:

A baseline event-driven microservices system

An agentic orchestration extension layered on top of it

2. Baseline Architecture: Event-Driven Microservices

The baseline implementation consists of the following components:

api_gateway

user_service_v1

user_service_v2 (Strangler Pattern migration)

order_service

RabbitMQ (Event Bus)

2.1 Communication Model

The system follows an event-driven architecture:

Services expose REST endpoints using FastAPI.

Domain events are published asynchronously.

Consumers subscribe to relevant message queues.

Direct service-to-service coupling is avoided.

2.2 Design Patterns Employed

Event-Driven Architecture

API Gateway Pattern

Strangler Pattern

Containerized Deployment Model

This baseline demonstrates horizontal scalability, isolation, and modular deployment.

3. Agentic Extension: Orchestrated Multi-Agent System

The second phase introduces an orchestration layer composed of:

orchestrator_service

user_agent

order_agent

3.1 Architectural Shift

The architectural model transitions from:

Request → Service → Response

to:

Goal → Orchestrator → Agents → Execution → Events

The Orchestrator interprets high-level goals and delegates domain-specific tasks to agents. Agents execute independently while remaining integrated within the event-driven infrastructure.

3.2 Agent Responsibilities
Component	Responsibility
Orchestrator	Task coordination and workflow delegation
User Agent	Execution of user-related operations
Order Agent	Execution of order-related operations
RabbitMQ	Asynchronous communication backbone
4. Comparative Architectural Analysis
4.1 Microservices Model

Strengths:

Independent deployability

Service isolation

Clear bounded contexts

Limitations:

Distributed coordination logic

Hard-coded workflow sequencing

Limited task abstraction

4.2 Agentic Model

Strengths:

Centralized workflow reasoning

Task delegation abstraction

Flexible coordination logic

Reduced coupling between domain logic and workflow logic

Trade-offs:

Increased orchestration complexity

Additional coordination latency

Dependency on orchestrator reliability

5. System Implementation
5.1 Technology Stack

Python (FastAPI)

RabbitMQ

Docker & Docker Compose

RESTful APIs

Asynchronous Messaging

Containerized Multi-Service Deployment

5.2 Deployment Modes
Baseline Microservices
docker-compose -f docker-compose.baseline.yml up --build
Agentic Architecture
docker-compose -f docker-compose.agent.yml up --build
6. Security Considerations

All environment secrets have been removed from repository history.

Configuration should be provided locally via:

OPENAI_API_KEY=
MONGO_URL=
RABBITMQ_URL=
JWT_SECRET=

The repository does not store production credentials.

7. Reliability and Distributed Systems Perspective

This project explores key distributed systems principles:

Fault isolation and blast radius containment

Asynchronous coordination

Event consistency boundaries

Orchestration overhead analysis

Service-to-agent architectural decoupling

The agentic layer introduces a coordination abstraction while preserving event-driven resilience properties.

8. Future Work

Potential extensions include:

Integration with structured agent frameworks (e.g., LangGraph)

Policy-based failure handling (fail-fast, fail-soft, fail-partial)

Persistent agent memory

AWS ECS Fargate deployment

Performance benchmarking between microservice and agentic modes

Automated orchestration decision metrics

9. Conclusion

This repository demonstrates a structured architectural evolution from an event-driven microservices system to an orchestrated agent-based distributed model.

Rather than replacing microservices, the agentic layer complements them by abstracting workflow coordination into a goal-driven orchestration framework.

The project serves as both:

A practical cloud programming implementation

A research-oriented exploration of distributed system architecture evolution
