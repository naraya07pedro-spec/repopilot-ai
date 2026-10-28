# Hosting preparation and exact external setup

Status: PARTIAL. The GitHub Pages demo remains deployed. Netlify publication is explicitly
pending at the owner's request. No paid service, new database, or worker was provisioned.
Private execution is still disabled in code; there is no environment switch to bypass it.

## Public frontend: Netlify

The repository's `netlify.toml` builds only `frontend/public-site`, publishing its `out`
directory at the domain root. It skips the Next.js server adapter and defines no functions,
API proxy or catch-all rewrite. No private application credentials belong on this site.
`.netlify/` is ignored so local account/site linkage cannot be committed.

External action: reconnect the intended Netlify account, select its free team, then import
this existing GitHub repository with main as the production branch. Do not deploy into a
different connected account. Confirm the team's included credits/usage and automatic recharge
settings before publication; no paid upgrade or overage is authorized. Reuse an existing
RepoPilot site if one appears. The connected tools can inspect/create a project but currently
do not provide Git linkage or artifact-upload operations, so Git import or an authenticated
CLI is needed to publish. Keep the working Pages URL until a Netlify HTTPS URL and its actual
browser flows pass. [Netlify static deployment guidance](https://www.netlify.com/knowledge-base/deploy-your-v0-app-to-netlify/)

Local root-path reproduction (POSIX shell):

```sh
cd frontend
npm ci
PUBLIC_BASE_PATH='' npm run build:public
npm run build
PUBLIC_BASE_PATH='' npm run test:browser
```

The browser suite checks actual diffs, results, the real PR link, mobile layout, script/style
responses and private-route 404s. CI tests both the Pages subpath and Netlify domain-root build.
This is evidence for the exported application; it does not claim Netlify itself has deployed.

## Supabase: reuse with an isolated private schema

Discovery found an accessible healthy project with existing application tables. Those tables
were not read or changed. No RepoPilot schema or role has been created remotely.

External actions in the selected existing project:

1. Review `deploy/private-schema.sql` and run it once through an administrator connection.
   It creates only `repopilot_private` and `repopilot_service`, initially with login disabled.
   It fails atomically if either already exists; inspect instead of dropping existing objects.
2. Set a generated password securely (for example, psql `\password repopilot_service`), then
   enable that role's login. It has no superuser, role-creation, database-creation, replication
   or RLS-bypass privilege. Use this role for RepoPilot, never the `postgres` administrator.
3. Obtain the project's actual connection endpoint from **Connect**. Use the direct endpoint
   on an IPv6-capable host, or the **session** pooler for an IPv4 host. Do not choose the
   transaction pooler for this profile. Mount the CA certificate supplied by the project.
4. Inject `DATABASE_URL` into the private backend, using SQLAlchemy's `postgresql+psycopg`
   driver, URL-encoded credentials, `sslmode=verify-full`, and a valid `sslrootcert` path.
   Set `REPOPILOT_DATABASE_SCHEMA=repopilot_private`. No connection string goes into Git,
   Netlify's public build, chat, or a `NEXT_PUBLIC_` variable.
5. Run `python scripts/migrate_database.py` with that private environment. Version 2 remains
   additive. Explicit SQLAlchemy schema qualification keeps all five application tables in
   the private schema. Migrations enable RLS and revoke schema/table access from PUBLIC,
   `anon` and `authenticated`. The dedicated table owner is the trusted backend principal;
   owner access bypasses RLS by PostgreSQL design. There are no browser database grants.
6. Verify sessions, concurrent idempotency and restart recovery through the deployed owner
   API. Keep the schema out of Data API exposed schemas and Realtime publications. Configure
   backups and retention before storing private source code. Do not change project-wide SSL,
   API or role settings that would affect the existing applications.

Production startup now rejects SQLite, the default/shared schemas and unverified database TLS.
The schema must already exist; startup never silently falls back to `public`.
[Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[certificate verification](https://supabase.com/docs/guides/platform/ssl-enforcement),
[SQLAlchemy schema translation](https://docs.sqlalchemy.org/en/20/core/connections.html#translation-of-schema-names).

## Private backend and owner UI: evaluated options

Reviewed against official documentation on 28 October 2026; prices and allowances can change.

| Platform | Current cost model | Fit for this project |
| --- | --- | --- |
| Render | Free web services; shared monthly allowance, idle sleep and ephemeral files | Suitable for a planning-only preview, with durable data in Supabase; not an availability commitment |
| Railway | Free tier includes $1 monthly credit; Hobby is $5/month plus usage beyond included credit | Possible container preview; running cost needs measurement and an explicit cap before paid use |
| Fly.io | Usage-billed Machines; no assumed permanent free allocation | Candidate for later VM execution research, requiring cost approval and separate isolation validation |

[Render free limits](https://render.com/docs/free), [Railway plans](https://docs.railway.com/pricing/plans),
[Fly.io pricing](https://fly.io/docs/about/pricing/).

`deploy/render-preview.yaml` is an optional reviewed configuration for two **free web services**:
the existing FastAPI image and the separate owner Next.js image. It creates no database or
worker and disables automatic deploys. Both services share Render's free-hour allowance;
two continuously running services can exhaust it. Free services sleep after inactivity and
can interrupt planning; persisted runs become `interrupted` on restart. They are not an
appropriate always-on production worker. The schema guard prevents losing durable state to
the ephemeral filesystem. [Blueprint format](https://render.com/docs/blueprint-spec)

External action: provide access to a selected Render account (or choose another reviewed
container host). Import this file only after checking available free capacity and disabling
chargeable overages/recharge. Supply the backend secrets from `deploy/owner.env.example`.
The private frontend receives only `REPOPILOT_ORIGIN` and `REPOPILOT_BACKEND`; both services
use the frontend's exact HTTPS origin for CSRF. Set the backend URL to the actual HTTPS API
endpoint. The free API endpoint is publicly routable but owner routes require authentication;
it is not a private-network service. For production, move to an approved private network and
ingress with request limits, monitoring and a tested database backup/restore procedure.

## Real model, App and execution worker

The remaining credentials are a least-privilege GitHub App installation/key, the chosen model's
server-side API key, current conservative token rates, and explicit USD limits per run/day.
Budget defaults remain zero. See `private-workspace.md`. The small-repository inspection limit
still applies; the project itself is larger than the current profile. A live planning task
needs an explicitly approved compatible scope before it sends source to a model.

No evaluated ordinary container tier establishes a hostile-code sandbox for this application.
The worker still needs implementation, not just credentials. A candidate must support a
disposable VM/microVM per run, no App/model/database secrets, denied egress and metadata access,
non-root execution, bounded CPU/memory/processes/storage/time, immutable input and evidence,
cancellation, cleanup and duplicate-write reconciliation. Adversarial tests must verify those
properties on the selected infrastructure before the private `/execute` route can be enabled.
[Fly Machines lifecycle](https://fly.io/docs/machines/overview/) is one option to evaluate after
approval; no claim is made that its defaults satisfy these controls.

There is no deployment URL for the private product and no live App/model/sandbox result yet.
