# FPX

Standalone service for collecting content from multiple source into single
file. Typical usecase is downloading multiple files as archive using single
link. Internally FPX fetches content from the specified set of URLs and streams
zip-compressed stream to the end users.


# Requirements

* Python v3.8 or newer
* DB driver. If you are using SQLite, no extra modules required. For other
  providers, install corresponding SQLAlchemy adapter. For example, if you are
  using PostgreSQL, install `psycopg2`:
  ```sh
  pip install psycopg2
  ```

  FPX has a set of predefined lists of dependencies for providers that were
  tested on development stage. You can just install all the required
  dependencies using package extra, when installing FPX itself:
  ```sh
  pip install 'fpx[postgresql]'
  ```

  Supported options are:

  * `postgresql`


# Installation

1. Install `fpx` package.
   ```sh
   pip install fpx
   ```

# Usage


# Complete Installation Guide (AmazonLinux)

1. Install Python 3.8 or newer using `pyenv`:
   ```sh
   # install build dependencies
   sudo yum install -y openssl-devel readline-devel zlib-devel bzip2-devel libffi-devel

   # install `pyenv`
   git clone https://github.com/pyenv/pyenv.git ~/.pyenv
   # this require `chmod +x $HOME` if you are going to use different user for running services with installed python executable
   echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
   echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
   echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile

   # install python
   pyenv install 3.8.2
   ```

1.  Create virtual environment for FPX and install it:
    ```sh
    pyenv shell 3.8.2
    cd ~/.virtualenvs
    python -m venv fpx
    cd fpx
    source bin/activate
    pip install 'fpx~=0.4.0'
    ```

1. Create config file. It can be created anywhere, as long as it accessible by FPX service:
   ```sh
    echo '
    PORT = 12321
    # DB is not used much, so SQLite can be used as long as you are going to use single instance of FPX service. If you planning to use multiple instances + load balancer, consider using PostgreSQL
    DB_URL = "sqlite:////home/user/.virtualenvs/fpx/fpx.db"
    # Any other options passed directly to the SQLAlchemy engine constructor(https://docs.sqlalchemy.org/en/13/core/engines.html#sqlalchemy.create_engine)
    DB_EXTRAS = {
      # "pool_size": 10,
      # "max_overflow": 20,
    }
    ' > /etc/fpx/fpx.py
    ```

1. Initialize database and create access token for client:
   ```sh
    export FPX_CONFIG=/etc/fpx/fpx.py
    fpx db up
    fpx client add my-first-fpx-client  # use any name, that match `[\w_-]`
    ```

   Make sure, db is accessible and writable by FPX service. This
   manual suggests using `apache` user when configuring supervisor's
   process, so following command required:
   ```sh
   chown apache:apache /home/user/.virtualenvs/fpx/fpx.db
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
    user=apache

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
   [documentation](https://sanic.readthedocs.io/en/latest/sanic/deploying.html#deploying),
   no additional layers required. But if you decide to use it with Nginx, the
   [following
   link](https://sanic.readthedocs.io/en/latest/sanic/nginx.html#nginx-configuration)
   may be useful. Note, if `FPX_NO_QUEUE` set to `False`, FPX is using
   websockets (if it can somehow affect configuration).

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

   Example of apache configuration:
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
