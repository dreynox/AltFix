# Northwind CLI

The Northwind CLI deploys your app and shows you what changed.

![](docs/terminal-output.png)

## Install

```
npm install -g northwind
```

## Dashboard

![Northwind dashboard showing total revenue and active users](docs/dashboard.png)

The dashboard shows how your deployment is doing.

<img src="docs/dashboard.png" alt="">

## Revenue

![Bar chart of revenue by quarter](docs/revenue-chart.png)

Revenue by quarter, comparing 2024 against 2023.

![Revenue by quarter][chart]

[chart]: docs/revenue-chart.png

## Architecture

![Flowchart of the request path through the API gateway](docs/architecture.png)

The client talks to the API gateway, which forwards to the auth service.

```bash
northwind deploy --env production
```

Build status: ![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
