# n8n Flows

Flow exports are in `n8n/flows`.

## Import Steps
1. Open n8n UI: [http://localhost:5678](http://localhost:5678)
2. Import each JSON file from this folder.
3. Update backend URL if needed (`http://backend-api:8000` inside Docker network).
4. Activate workflows.

## Flows
- `incident_narrator.json`: webhook-triggered incident narrative + brief note
- `exec_brief_generator.json`: daily 09:00 executive brief draft
- `anomaly_correlator.json`: anomaly cause ranking with citations

## Demo Mode
Slack delivery is mocked through a generic HTTP node and backend logging. Replace with Slack node in production.
