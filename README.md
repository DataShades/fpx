# FPX

Standalone service for collecting content from multiple source into single
file. Typical usecase is downloading multiple files as archive using single
link. Internally FPX fetches content from the specified set of URLs and streams
zip-compressed stream to the end users.

# Installation

1. Install `fpx` package
   ```sh
   pip install fpx
   ```
1. Initialize DB
   ```sh
   fpx db up
   ```
1. Start FPX server
   ```sh
   fpx server run
   ```

# Usage

## Authentication

Majority of FPX endpoints are available only via *client's secret*. It can be
generated via CLI command(replace `<CLIENT_NAME>` with an arbitrary combination
of letters, digits and underscores):

```sh
fpx client add <CLIENT_NAME>
```

And secret will be shown in the output of the command:

```sh
Client created: <CLIENT_NAME> - <SECRET>
```

Pass the secret via `Authorization` header with each request to identify
yourself as a client.

## Downloads

Downloading a file via FPX usually consists of two steps:

* Provide information about downloaded URLs and receive IDs of the *download ticket*
* Use the ticket's ID to download all URLs packed into a single ZIP archive

First step can be completed via cURL:

```sh
curl -X POST http://localhost:8080/ticket/generate \
    -H "Authorization: <CLIENT_SECRET>" \
    -d '{"items":["https://google.com", "https://google.com/search"]}'
```

Here we are making a POST request to `/ticket/generate` endpoint of FPX
service. It's requires client's secret, which is specified by `Authorization`
header. This endpoint works only with JSON requests, that's why we need
`Content-type`. Finally, body of the request must contain a JSON with an
`items` field: the list of all URLs we are going to download.

Response will be the following:
```sh
{"created":"2023-10-15T00:00:51.054523","type":"zip","id":"ca03e214-910d-419f-ad60-4b6fb8bdd10c"}
```

You need only `id` field from it. Use it to make a download URL:
`/ticket/<ID>/download`. For the example above we receive this URL:
`http://localhost:8080/ticket/ca03e214-910d-419f-ad60-4b6fb8bdd10c/download`.

Open it in web browser or use `wget`/`curl` to download file via CLI:

```sh
curl http://localhost:8080/ticket/ca03e214-910d-419f-ad60-4b6fb8bdd10c/download -o collection.zip
```

# Configuration

FPX works without explicit configuration, but default values are not suitable
for production environments. Config options can be changes via config file and
environment variables.

## Config file

FPX config file is a python script. It's read by FPX and all global variables
from it are used as config options. For example, the following file will add
`A` and `B` options to FPX application:

```python
A = 1
B = ["hello", "world"]
```

Path to this file must be specified via `FPX_CONFIG` environment variable:

```
export FPX_CONFIG=/etc/fpx/config/fpx.py
fpx server run
```

## Environment variables

In addition to config file, FPX reads all environment variables with `FPX_*`
name, strips `FPX_` prefix and use result as a config option. I.e:
* `FPX_DB_URL` envvar turns into `DB_URL` config option
* `FPX_FPX_TRANSPORT` envvar turns into `FPX_TRANSPORT` config option.

Pay attention to config options with the name starting with `FPX_`. Because
`FPX_` prefix is removed from envvars, you have to repeat it twice, like in
`FPX_FPX_TRANSPORT` above.

## Config options

FPX makes use of the following config options

| Name            | Description                                                                        | Default                 |
|-----------------|------------------------------------------------------------------------------------|-------------------------|
| `DEBUG`         | Run application in debug mode. Mainly used for development                         | false                   |
| `HOST`          | Bind application to the specified addres                                           | 0.0.0.0                 |
| `PORT`          | Run application on the specified port                                              | 8000                    |
| `DB_URL`        | DB URL used for SQLAlchemy engine                                                  | `sqlite:////tmp/fpx.db` |
| `FPX_TRANSPORT` | Underlying library for HTTP requests. `aiohttp` and `htmx` supported at the moment | `aiohttp`               |

# Complete Installation Guide

1. Install FPX:
   ```sh
   pip install fpx
   ```

1. Create config file. It can be created anywhere, as long as it accessible by FPX service:
   ```sh
   echo '
   PORT = 12321
   DB_URL = "sqlite:////home/user/.virtualenvs/fpx/fpx.db"
   ' > /etc/fpx/fpx.py
   ```

1. Initialize database and create access token for client:
   ```sh
   export FPX_CONFIG=/etc/fpx/fpx.py
   fpx db up
   fpx client add my-first-fpx-client  # use any name, that match `[\w_-]`
   ```

   Make sure, db is accessible and writable by FPX service. This
   manual suggests using `www-data` user when configuring supervisor's
   process, so following command required:
   ```sh
   chown www-data:www-data /home/user/.virtualenvs/fpx/fpx.db
   ```

1. Test service:
   ```sh
    FPX_CONFIG=/etc/fpx/fpx.py fpx server run
    # or, if you want to explicitely use python interpreter
    FPX_CONFIG=/etc/fpx/fpx.py python -m fpx
    ```

1. Configure system.d/supervisor/etc. unit for fpx. Make sure, that
   `fpx server run` command, that spins up the service is executed using
   python>=3.6 (`pyenv shell 3.8.2`). And, if SQLite is used, fpx
   process has write access to db file:
   ```ini
   [program:fpx-worker]

   ; Use the full paths to the virtualenv and your configuration file here.
   command=/home/user/.virtualenv/fpx/bin/python -m fpx

   environment=FPX_CONFIG=/etc/fpx/fpx.py

   ; User the worker runs as.
   user=www-data

   ; Start just a single worker. Increase this number if you have many or
   ; particularly long running background jobs.
   numprocs=1
   process_name=%(program_name)s-%(process_num)02d

   ; Log files.
   stdout_logfile=/var/log/fpx-worker.log
   stderr_logfile=/var/log/fpx-worker.log

   ; Make sure that the worker is started on system start and automatically
   ; restarted if it crashes unexpectedly.
   autostart=true
   autorestart=true

   ; Number of seconds the process has to run before it is considered to have
   ; started successfully.
   startsecs=10

   ; Need to wait for currently executing tasks to finish at shutdown.
   ; Increase this if you have very long running tasks.
   stopwaitsecs = 600
   ```

1. FPX service must be available via public url. As written in
   [documentation](https://sanic.dev/en/guide/deployment/running.html#running-sanic),
   no additional layers required. But if you decide to use it with Nginx, the
   [following
   link](https://sanic.dev/en/guide/deployment/nginx.html#proxied-sanic-app)
   may be useful. Note, if `FPX_NO_QUEUE` config option is set to `False`, FPX
   is using websockets (and it can affect configuration).

   Example of Nginx section for FPX:
   ```conf
   location /fpx/ {
      proxy_pass http://127.0.0.1:12321/;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header Host $host;
      proxy_http_version 1.1;
      proxy_request_buffering off;
      proxy_buffering off;

      # When FPX_NO_QUEUE option set to `False`
      proxy_set_header connection "upgrade";
      proxy_set_header upgrade $http_upgrade;

      # In emergency comment out line to force caching
      # proxy_ignore_headers X-Accel-Expires Expires Cache-Control;
   }
   ```

   Example of httpd configuration:
   ```cond
   # mod_proxy
   # mod_proxy_http
   ProxyPass /fpx/ http://0.0.0.0:8000/
   ProxyPassReverse /fpx/ http://0.0.0.0:8000/

   # When FPX_NO_QUEUE option set to `False`
   # mod_proxy_wstunnel
   # mod_rewrite
   RewriteEngine on
   RewriteCond %{HTTP:UPGRADE} ^WebSocket$ [NC]
   RewriteCond %{HTTP:CONNECTION} ^Upgrade$ [NC]
   RewriteRule /fpx/(.*) ws://0.0.0.0:8000/$1 [P]
   ```
