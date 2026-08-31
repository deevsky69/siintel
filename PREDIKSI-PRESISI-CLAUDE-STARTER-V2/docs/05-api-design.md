# API DESIGN — WORKING DOCUMENT

This file will become the contract between the web frontend, backend, and future Android app.

## Conventions
- REST API initially.
- JSON request/response.
- Server-side authorization.
- Consistent error format.
- Pagination for lists.
- Filtering and date/time ranges for analytical queries.
- No direct database access from clients.

## Initial Resource Groups

### Authentication
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

### Crimes
GET  /api/crimes
GET  /api/crimes/{id}
POST /api/crimes

### Map
GET /api/map/incidents
GET /api/map/historical-heatmap
GET /api/map/predictive-heatmap

### Risk
GET /api/risk-scores
GET /api/risk-scores/{area}

### Prediction
GET /api/predictions
GET /api/predictions/{id}
POST /api/predictions/run

### Warning
GET /api/warnings
GET /api/warnings/{id}
POST /api/warnings/{id}/acknowledge

### Recommendation
GET /api/recommendations
GET /api/recommendations/{id}

### Commander Decision
POST /api/recommendations/{id}/approve
POST /api/recommendations/{id}/modify
POST /api/recommendations/{id}/reject

### Evaluation
GET /api/evaluation/summary
GET /api/evaluation/prediction-vs-actual

Exact schemas and authorization rules must be finalized before production use.
