# AGENTS.md

# Project Overview

This repository contains a global enterprise-grade Microsoft Fabric Custom Workload.

The workload is intended to be distributed through Microsoft Marketplace / AppSource and installed by customers directly inside Microsoft Fabric environments.

The solution is designed as:
- multi-tenant
- modular
- metadata-driven
- configuration-driven
- highly extensible
- enterprise scalable

The workload ingests data from:
- Microsoft Dataverse / Dynamics 365 CRM
- Dynamics 365 Business Central
- SQL Server / Azure SQL

Primary goal:
- ingest raw operational data
- land data into Bronze storage
- prepare semantic-ready structures
- support future medallion architecture evolution

---

# Primary Architectural Principles

All implementations MUST follow:

- modular architecture
- separation of concerns
- clean architecture principles
- enterprise DevOps practices
- cloud-native patterns
- secure-by-default principles
- observable systems design
- highly parameterized configuration
- metadata-driven orchestration
- minimal hardcoded logic
- tenant isolation
- extensibility-first design

Avoid:
- tightly coupled implementations
- customer-specific hardcoding
- duplicated orchestration logic
- hidden configuration
- static assumptions
- environment-specific logic in source code

---

# Repository as Source of Truth

Agents MUST:
- analyze the entire repository
- understand existing architectural patterns
- reuse existing abstractions
- follow repository conventions
- avoid introducing conflicting patterns

Do not rely only on markdown documentation.
Infer intended architecture directly from implementation when needed.

---

# Product Vision

The workload acts as a Fabric-native ingestion and semantic preparation platform.

Customers must be able to:
- install the workload from marketplace
- configure ingestion using a wizard UI
- enable only selected modules
- onboard sources quickly
- monitor ingestion health
- manage semantic preparation

The product must scale globally across many tenants and customers.

---

# Module Architecture

The platform MUST support independently deployable modules.

Current modules:
- CRM / Dataverse
- Business Central
- SQL Server / Azure SQL

Future modules must be easy to add without major refactoring.

Modules MUST:
- share common infrastructure
- share orchestration standards
- share metadata standards
- share observability standards
- remain independently configurable

---

# CRM / Dataverse Priority

CRM ingestion is the first delivery priority.

Primary focus:
- Dynamics 365 Marketing
- Customer Insights
- Dataverse entities

Agents should prioritize:
- near real-time ingestion
- change tracking
- scalable synchronization
- operational resilience
- schema evolution handling

Initial implementation includes:
- 5 marketing-related entities

Agents must evaluate:
- Link to Fabric
- Open Mirroring
- Synapse Link
- Dataverse APIs
- Fabric-native patterns
- CDC approaches

All architectural decisions must explain:
- tradeoffs
- operational impact
- scalability implications
- maintainability implications

---

# Business Central Module

Business Central ingestion must use:
- official APIs
- incremental extraction
- scalable retry patterns
- configurable synchronization

Initial scope:
- Customers entity

Design for:
- throttling handling
- pagination
- retries
- extensibility

---

# SQL Module

SQL ingestion should evaluate:
- Fabric Mirroring
- CDC
- hybrid ingestion
- mirrored database approaches

Architecture must support:
- near real-time synchronization
- replayability
- operational observability

---

# Storage Architecture

Agents must evaluate:
- Lakehouse Bronze
- Mirrored Database patterns

Storage decisions must consider:
- semantic model compatibility
- scalability
- operational complexity
- cost
- performance
- future extensibility

---

# Bronze Layer Standards

Bronze layer MUST:
- preserve raw source fidelity
- remain immutable
- support replayability
- support lineage
- support auditing
- support CDC metadata
- support ingestion timestamps
- support schema evolution

Do not introduce business logic into Bronze.

---

# Semantic Layer Preparation

The workload must prepare:
- semantic-ready structures
- standardized naming
- metadata-driven semantic scaffolding

Business logic should remain separated from ingestion logic.

---

# Configuration Standards

Configuration MUST be JSON-driven.

Configuration categories:
- tenant configuration
- source configuration
- authentication
- ingestion settings
- scheduling
- feature flags
- semantic model generation
- deployment settings

Avoid hardcoded values.

---

# UI / UX Standards

The workload includes a custom Fabric UI.

The UI must provide:
- onboarding wizard
- source setup
- authentication setup
- ingestion monitoring
- logs
- health dashboards
- module enablement
- semantic setup

UX principles:
- guided
- enterprise-friendly
- low-friction
- scalable
- maintainable

---

# DevOps Standards

All implementations MUST support:
- CI/CD
- GitOps
- Infrastructure as Code
- automated testing
- rollback strategies
- versioning
- release pipelines

Agents should prefer:
- reusable pipelines
- reusable deployment templates
- environment abstraction

---

# Documentation Standards

Documentation is mandatory.

All major implementations MUST include:
- architectural explanation
- operational explanation
- deployment explanation
- configuration explanation
- troubleshooting guidance

Documentation must remain:
- updated
- precise
- implementation-aligned

---

# Security Standards

All implementations MUST:
- follow least privilege principles
- support secure secret handling
- avoid storing secrets in code
- support OAuth flows
- support tenant isolation
- support RBAC compatibility

---

# Coding Standards

Prefer:
- strongly typed implementations
- composable abstractions
- reusable services
- dependency injection
- async patterns
- centralized configuration
- clear interfaces

Avoid:
- large monolithic services
- hidden side effects
- duplicated orchestration logic

---

# Agent Behavior Rules

Agents MUST:
- explain architectural reasoning
- explain tradeoffs
- explain alternatives
- identify risks
- identify scalability concerns
- identify operational concerns

Before implementing:
- analyze existing patterns
- verify consistency
- verify extensibility impact

When uncertain:
- prefer extensibility
- prefer maintainability
- prefer modularity
- prefer operational simplicity

---

# Long-Term Vision

This workload should evolve into a globally distributed enterprise-grade Microsoft Fabric ingestion and semantic preparation platform.

All architectural decisions should optimize for:
- long-term maintainability
- scalability
- extensibility
- operational excellence
- marketplace readiness
- multi-tenant SaaS evolution