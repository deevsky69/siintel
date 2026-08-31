# ROLE-PERMISSION MATRIX — WORKING DRAFT

Legend:
R = Read
W = Create/Write
A = Approve
- = No access
L = Limited / jurisdiction-scoped

| Module | Pimpinan | Command Center | Analyst | Fungsi | Polsek | Admin |
|---|---|---|---|---|---|---|
| Dashboard | R | R | R | L | L | R |
| Crime Data | L | R | RW | RW | RW(L) | R |
| Map | R | RW | RW | R | R(L) | R |
| Analytics | R | R | RW | L | L | R |
| Prediction | R | R | RW | R | L | R |
| Risk Score | R | R | RW | R | L | R |
| Early Warning | R | RW | RW | R | L | R |
| Recommendation | RA | RW | RW | R | L | R |
| Commander Decision | A | - | - | - | - | - |
| Evaluation | R | R | RW | L | L | R |
| User Management | - | - | - | - | - | RW |
| Audit Logs | R | R | R | L | L | RW |

This is a working draft. Final permissions must follow the authorized operational model.
