# Architecture

This document describes how a request travels through the system.

![Request flow diagram](docs/request-flow.png)

The client calls the API gateway, which forwards to the auth service and the
database.

<picture>
  <source srcset="docs/request-flow.png" type="image/png">
  <img src="docs/request-flow.png" alt="A flowchart with four boxes connected by arrows">
</picture>

## Branding

![Northwind](docs/northwind-logo.png)

The wordmark used across the project.
