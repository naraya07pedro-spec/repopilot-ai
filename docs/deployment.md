# Deployment and rollback

## Public evidence site

The static Next.js app in `frontend/public-site` includes exactly three approved recordings.
It has no API routes, credentials, login, model calls or code execution. The separate owner
Next.js app must never be substituted into this static deployment.

1. In the existing repository, Settings -> Pages -> Source: GitHub Actions.
2. Run the existing Public demo workflow from `feat/v2-public-private` (later `main` after review).
3. The workflow builds with `PUBLIC_BASE_PATH=/repopilot-ai`, uploads `frontend/public-site/out`,
   and deploys with Pages and OIDC permissions. Observe environment restrictions normally.
4. Verify the deployment's returned HTTPS URL, asset requests and interactive evidence tabs.

The owner reported selecting GitHub Actions source, but fresh metadata still returned
has_pages=false. The deployment retry again failed at configure-pages with site-not-found,
and a direct HTTPS request returned 404. This remains a setting/access blocker, not a build failure.
The intended address is `https://naraya07pedro-spec.github.io/repopilot-ai/`; it is **not a
verified deployment** until the job and HTTP checks pass. Netlify connections also required
reauthentication; no Netlify site or paid infrastructure was created.

To reproduce the static build:

```sh
cd frontend
npm ci
PUBLIC_BASE_PATH=/repopilot-ai npm run build:public
node scripts/serve-public.mjs
# http://127.0.0.1:4173/repopilot-ai/
```

The server is for loopback tests only. GitHub serves HTTPS for the actual Pages deployment.
Configuration follows [GitHub's official workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Private control plane (not deployed)

Run the existing FastAPI and Next.js images on a private network behind an HTTPS reverse
proxy, with PostgreSQL on a persistent volume. `compose.yaml` is a local fixture setup,
not production configuration: its demonstration database password must not be deployed.
No hosting credentials, production database or isolated worker were available for verification.
Use `private-workspace.md` for exact environment variables. Only the Next.js proxy should be
internet-facing; configure request-size/time limits and rate limits at ingress. Preserve the
public Origin when proxying to Next.js. Terminate TLS at a managed ingress and use secure cookies.

Before startup, back up the database, install the locked dependencies including `[postgres]`,
set `DATABASE_URL=postgresql+psycopg://...`, and run `python scripts/migrate_database.py`.
Schema version 2 adds sessions, private runs and daily model reservations without dropping V1
runs. Startup repeats the idempotent migration. It supports one service process; do not start
multiple replicas. SQLite remains available for local development, not the production recommendation.

Check `/health` and authenticated `/api/owner/settings`. Route structured `repopilot.http`
JSON logs to the host log service; request IDs, method, path, status and elapsed time are logged,
not request bodies, credentials or repository source. No external error-monitoring account is
configured. Alert on health failures and interrupted/failed runs. Back up private records and
set a retention policy before accepting sensitive repositories.

There is no worker deployment artifact claiming safe arbitrary execution. A separate disposable
VM/microVM executor still requires implementation and adversarial validation: no secrets,
denied network, non-root identity, bounded filesystem/CPU/memory/processes/time, cancellation,
cleanup and immutable evidence transfer. Until it passes review, execution is disabled.

## Rollback

Redeploy a previously verified static artifact from the same workflow and check its URL.
For the private app, stop the service, preserve a database backup and deploy the previous
reviewed image. Additive V2 tables may remain when rolling back to V1; do not drop evidence.
V1 must remain loopback-only. Restore a database backup only with explicit operator approval,
since that can discard newer runs and budget reservations. No rollback was exercised against
production infrastructure because none was provisioned.
