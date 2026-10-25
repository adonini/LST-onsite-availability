# LST-onsite-availability

This repository contains a legacy Dash/MongoDB application and a Django calendar application.

## Django app

The Django application lives in `django_cal_app/`. Its production configuration is
`django_cal_app/docker-compose.prod.yml`; the existing `docker-compose.yml` is for
local development. Do not combine the two Compose files. Use different Compose
project names if both stacks run on the same host.

### Required production files and directories

On the production host, provide:

| Item | Where it is mounted | Purpose |
| --- | --- | --- |
| `django_cal_app/.env.prod` | Loaded by Compose, not copied into the image | Django secret, hostnames, HTTPS and SMTP settings |
| `/home/lst1/lst-onsite-availability/db_data/db.sqlite3` | `/data/db.sqlite3` in `app` | Persistent SQLite database |
| `/home/www/git/lst.iac.es/website/public/travel/lst1_events.json` | `/data/onsite/lst1_events.json` (read-only) | External onsite events |

The database directory must already exist and be writable by the app container.
If migrating an existing deployment, verify the database file at this path is
the one currently in use **before** starting the new stack. Back it up using
SQLite's online backup mechanism and test a restore. Never put the production
database, `.env.prod`, or copied event data in Git.

Copy `django_cal_app/production.env.example` to `django_cal_app/.env.prod` and
replace the placeholder secret with a long, random `DJANGO_SECRET_KEY`. The
example has the production database and event JSON paths above. Review
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, email settings, and the
proxy address. Both `calendar.lst.iac.es` and `calendar.lst1.iac.es` are
configured by default. The previous secret should be retained when migrating
an existing database so existing sessions and signed tokens remain valid.

### HTTPS proxy

The Compose stack exposes HTTP on `${PROD_BIND_IP}:${PROD_PORT}` (port 8088 by
default). TLS must terminate at the trusted external proxy, which must forward
the original `Host` and **overwrite** `X-Forwarded-Proto` with `https` for HTTPS
requests. Only that proxy should be able to reach the published port; use
`PROD_BIND_IP=127.0.0.1` when the proxy is on the same host, or a private IP
and firewall rules when it is remote. Do not expose this HTTP port publicly.
`DJANGO_TRUST_PROXY_SSL_HEADER=true` is safe only with that trusted-proxy setup.

### Build and start

From `django_cal_app/` on the production host:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml -p lst-calendar-prod config
docker compose --env-file .env.prod -f docker-compose.prod.yml -p lst-calendar-prod build
docker compose --env-file .env.prod -f docker-compose.prod.yml -p lst-calendar-prod up -d
docker compose --env-file .env.prod -f docker-compose.prod.yml -p lst-calendar-prod exec app python manage.py check --deploy
```

`check --deploy` may report optional HSTS subdomain/preload warnings. Do not
enable either setting unless every subdomain of the shared domain is owned and
HTTPS-ready; the example enables HSTS for the calendar host only.

The app runs committed migrations and collects static files at startup. It
will fail to start if either step fails; it does not generate migrations or
create a superuser automatically. For a new database only, create the initial
admin account explicitly:

```sh
docker compose --env-file .env.prod -f docker-compose.prod.yml -p lst-calendar-prod exec app python manage.py createsuperuser
```

Before each deployment, back up the database, build the new image, start the
stack, verify health and login through the HTTPS domain, and test the calendar,
on-call contact links, profile editing, and email delivery. Keep the previous
image/commit and a restorable database backup available for rollback. Do not
run `docker compose down -v`: it deletes named volumes containing static files
and logs.

### Local production-like smoke test

Use a **different** Compose project and an isolated SQLite directory. Copy
`production.env.example` to ignored `.env.prod.local`, set
`APP_ENV_FILE=.env.prod.local`, point `PROD_DB_DIR` to a new local directory
containing either a fresh database or a SQLite backup of the development
database, and set `PROD_EVENTS_JSON` to a local copy of the events JSON. Set
`PROD_BIND_IP=127.0.0.1`, `PROD_PORT=18088`,
`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`,
`DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:18088`,
`DJANGO_SECURE_COOKIES=false`, `DJANGO_SECURE_SSL_REDIRECT=false`,
`DJANGO_SECURE_HSTS_SECONDS=0`, and `DJANGO_TRUST_PROXY_SSL_HEADER=false`.
These HTTP-only settings are **only for the local smoke test**, not production.

```sh
docker compose --env-file .env.prod.local -f docker-compose.prod.yml -p lst-calendar-smoke build
docker compose --env-file .env.prod.local -f docker-compose.prod.yml -p lst-calendar-smoke up -d
docker compose --env-file .env.prod.local -f docker-compose.prod.yml -p lst-calendar-smoke exec app python manage.py test calendar_app.tests
```

Open `http://localhost:18088/`. This verifies the production image, mounts,
migrations, static assets, and application flows without touching the real
database. Repeat the HTTPS/security checks through the real proxy before
deployment; the local HTTP test cannot validate TLS or secure cookies.


## Dash app

### MongoDB

To start the container: `docker-compose up -d`

To stop the container: `docker-compose down`

The option `-d` detach the docker-compose, so that the container is being run in the background.

To list the running containers: `docker ps`.

To enter inside the Mongo container and run an interactive shell: `docker exec -it mongodb-av bash`.

### Logs

In the log file of the dash app is possible to find records of any delete/add action on the calendar.
