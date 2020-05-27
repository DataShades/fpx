FPX
===

AWS EC2 Deploy
---

1. Install Python 3.8 or newer::

     # install build dependencies
     sudo yum install -y openssl-devel readline-devel zlib-devel bzip2-devel libffi-devel

     # install `pyenv`
     git clone https://github.com/pyenv/pyenv.git ~/.pyenv
     echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
     echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
     echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile

     # install python
     pyenv install 3.8.2


2.  Create venv for FPX and install it::

      pyenv shell 3.8.2
      cd /usr/lib/ckan
      python -m venv fpx
      cd fpx
      source bin/activate
      pip install fpx

3. Create config file. It can be created anywhere, as long as it
   accessible by FPX service::

     echo '

     PORT = 8000

     # DB is not used much, so SQLite can be used as long as you are going to use single instance of FPX service.
     # If you planning to use multiple instances + load balancer, consider using PostgreSQL
     DB_URL = "sqlite:////etc/ckan/default/fpx.db"

     # Maximum number of simultaneous downloads. 2 is used only for testing.
     # In production, value between 10 and 100 should be used, depending on server's bandwidth.
     # Higher value won't create any performance penalty.
     SIMULTANEOURS_DOWNLOADS_LIMIT = 2
     ' > /etc/ckan/default/fpx.py

4. Initialize database and create access token for client. It can be
   stored later inside CKAN ini file as `fpx.client.secret`::

     export FPX_CONFIG=/etc/ckan/default/fpx.py
     fpx db up
     fpx client add link-digital  # use any name instead of `link-digital`

5. Test service::

     FPX_CONFIG=/etc/ckan/default/fpx.py fpx server run
     # or, if you want to explicitely use python interpreter
     FPX_CONFIG=/etc/ckan/default/fpx.py python -m fpx

6. Configure system.d/supervisor/etc. unit for fpx. Make sure, that
   `fpx server run` command, that spins up the service executed using
   python>=3,8 (`pyenv shell 3.8.2`) and, if SQLite is used, fpx
   process requires write access to db file.

7. FPX service must be available via public url(and CKAN ini file
   requires this URL under `fpx.service.url` config option). As
   written in
   documentation(https://sanic.readthedocs.io/en/latest/sanic/deploying.html#deploying),
   no additional layers required. But if you decide to use it with
   Nginx, following link may be useful -
   https://sanic.readthedocs.io/en/latest/sanic/nginx.html#nginx-configuration
   . Note, FPX is using websockets(if it can somehow affect configuration).
