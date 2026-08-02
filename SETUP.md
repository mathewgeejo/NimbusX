# NimbusX setup

## Prerequisites

- Docker Desktop with Compose, or Python 3.12+ and Node.js 22+ for native development.
- Internet access for real NASA POWER baseline requests.
- Forecast, Copernicus seasonal, and scenario retrieval are intentionally unavailable in this foundation. They return an explicit unavailable result; credentials alone do not enable a demo mode.

## Docker development

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Services:

- Workspace: <http://localhost:8080>
- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/healthz>
- Readiness: <http://localhost:8000/readyz>

Stop the stack with `docker compose down`. Add `--volumes` only when intentionally removing local database/cache data.

## Native development

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --require-hashes -r .\backend\requirements.lock
pip install --no-deps --no-build-isolation -e .\backend
uvicorn nimbusx.main:app --app-dir backend --reload --port 8000
```

Frontend:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

The Vite development server runs at <http://localhost:5173> and targets `http://localhost:8000` by default. Set `VITE_API_BASE_URL` only when the API is served elsewhere.

## Smoke test

```powershell
Invoke-RestMethod http://localhost:8000/healthz

$body = @{
  site = @{ name = 'New York facility'; latitude = 40.7128; longitude = -74.0060; timezone = 'America/New_York' }
  window = @{ start = '2032-07-15T09:00:00-04:00'; end = '2032-07-15T17:00:00-04:00' }
  mode = 'baseline'
  asset = @{ template = 'facility'; exposure = @{ criticality = 3 }; vulnerability = @{ backup_power = $true } }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/analyses -ContentType application/json -Body $body
```

Use the returned ID with `GET /v1/analyses/{id}`. A real NASA query may take longer than a local validation response; source failure must result in `partial` or `failed`, never invented data.

## Dependency locks

`backend/requirements.lock` is the full development/test lock used by native
backend development and CI. `backend/requirements.runtime.lock` is the smaller
runtime-only lock used by the API and data-plane Dockerfiles. Both are generated
from `backend/pyproject.toml`; regenerate them together with the pinned
`pip-tools` command after intentionally changing dependency constraints.
## Quality commands

```powershell
python -m pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

## Troubleshooting

- **NASA request unavailable:** check network access and retry later. Review the returned `data_gaps` and source evidence instead of trusting an old result.
- **Forecast/seasonal/scenario unavailable:** these adapters are intentionally not implemented in the foundation; the explicit unavailable result is expected.
- **Browser API error:** verify `NIMBUSX_CORS_ORIGINS` or `VITE_API_BASE_URL` matches the API origin.
- **Docker stale state:** use `docker compose down` before rebuilding. Do not remove volumes unless the local data may be discarded.
