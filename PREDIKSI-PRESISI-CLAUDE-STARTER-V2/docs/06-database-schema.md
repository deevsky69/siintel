# DATABASE SCHEMA IMPLEMENTATION GUIDE

Baseline: PostgreSQL + PostGIS untuk kebutuhan geospasial.

## Closed-loop
```text
DATA
 ↓
ANALYSIS
 ↓
PREDICTION
 ↓
EARLY WARNING
 ↓
RECOMMENDATION
 ↓
COMMANDER DECISION
 ↓
OPERATIONAL ACTION
 ↓
EVALUATION
 ↓
MODEL UPDATE
```

Siklus ini mengikuti arsitektur closed-loop pada dokumen PREDIKSI PRESISI. fileciteturn2file3

## Constraints
- `risk_score`, `confidence`, `urgency_score`, `verification_score`: 0..100.
- Foreign key harus valid.
- Prediction → location.
- Warning → prediction.
- Recommendation → prediction.
- Commander decision → recommendation.
- Operational action → commander decision.
- Prediction actual → prediction.
- Audit → user (nullable untuk system events).

## Belum final
Jangan mengarang atau mengunci:
- bobot risk score;
- threshold warning;
- algoritma ML;
- taxonomy final;
- retensi data;
- SLA;
- integrasi eksternal.

Nilai tersebut belum ditetapkan secara final dalam dokumen sumber.
