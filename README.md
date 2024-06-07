# Base FastAPI Template

<!-- PROJECT SHIELDS -->

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<p align="center">
<!-- PROJECT LOGO -->
<br />

<p align="center">
  <a href="https://github.com/felix-liuyj/base-fastapi-template">
    <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" alt="Logo" width="250" height="90">
  </a>

<h3 align="center">Base FastAPI Template</h3>
  <p align="center">
    Backend Template For FastAPI
    <br />
    <a href="https://github.com/felix-liuyj/base-fastapi-template"><strong>Check the documentation for details »</strong></a>
    <br />
    <br />
    <a href="https://github.com/felix-liuyj/base-fastapi-template">Demo</a>
    ·
    <a href="https://github.com/felix-liuyj/base-fastapi-template/issues">Report Bugs</a>
    ·
    <a href="https://github.com/felix-liuyj/base-fastapi-template/issues">New Issues</a>
  </p>
</p>

## Catalogue

- [Getting Started](#getting-started)
    - [Before Coding](#before-coding)
    - [Install Steps](#install-steps)
- [Catalogue Description](#catalogue-description)
- [Dependent Modules](#dependent-modules)

### Getting Started

###### Before Coding

1. Python ver: 3.11
2. pipenv
3. Docker
4. Jenkins
5. Kafka
6. Redis

###### **Install Steps**

1. Clone the repo

```sh
git clone git clone git@github.com:felix-liuyj/base-fastapi-template.git
pip install pipenv
cd .
pipenv install
pipenv shell
uvicorn main:app --host localhost --port 8080
```

### Catalogue Description

```
├── /app/
│  ├── /api/
│  ├── /config/
│  ├── /forms/
│  ├── /libs/
│  ├── /models/
│  ├── /statics/
│  ├── /templates/
│  └── /view_models/
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Jenkinsfile
├── main.py
├── Pipfile
├── Pipfile.lock
├── README.md
└── RuntimDockerfile

```

### Dependent Modules

- [uvicorn = "*"](https://pypi.org/project/uvicorn)
- [pydantic = "*"](https://pypi.org/project/pydantic)
- [bcrypt = "*"](https://pypi.org/project/bcrypt)
- [pycryptodome = "*"](https://pypi.org/project/pycryptodome)
- [fastapi = "*"](https://pypi.org/project/fastapi)
- [pyjwt = "*"](https://pypi.org/project/pyjwt)
- [motor = "*"](https://pypi.org/project/motor)
- [beanie = "*"](https://pypi.org/project/beanie)
- [jinja2 = "*"](https://pypi.org/project/jinja2)
- [pandas = "*"](https://pypi.org/project/pandas)
- [rich = "*"](https://pypi.org/project/rich)
- [httpx = "*"](https://pypi.org/project/httpx)
- [web3 = "*"](https://pypi.org/project/web3)
- [base58 = "*"](https://pypi.org/project/base58)
- [aiokafka = "*"](https://pypi.org/project/aiokafka)
- [redis = "*"](https://pypi.org/project/redis)
- [fastapi-cache2 = "*"](https://pypi.org/project/fastapi-cache2)
- [python-dotenv = "*"](https://pypi.org/project/python-dotenv)
- [python-dateutil = "*"](https://pypi.org/project/python-dateutil)
- [python-jenkins = "*"](https://pypi.org/project/python-jenkins)
- [email-validator = "*"](https://pypi.org/project/email-validator)
- [oss2 = "*"](https://pypi.org/project/oss2)

<!-- links -->

[contributors-shield]: https://img.shields.io/github/contributors/felix-liuyj/base-fastapi-template.svg?style=flat-square

[contributors-url]: https://github.com/felix-liuyj/base-fastapi-template/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/felix-liuyj/base-fastapi-template.svg?style=flat-square

[forks-url]: https://github.com/felix-liuyj/base-fastapi-template/network/members

[stars-shield]: https://img.shields.io/github/stars/felix-liuyj/base-fastapi-template.svg?style=flat-square

[stars-url]: https://github.com/felix-liuyj/base-fastapi-template/stargazers

[issues-shield]: https://img.shields.io/github/issues/felix-liuyj/base-fastapi-template.svg?style=flat-square

[issues-url]: https://img.shields.io/github/issues/felix-liuyj/base-fastapi-template.svg

[license-shield]: https://img.shields.io/github/license/felix-liuyj/base-fastapi-template.svg?style=flat-square

[license-url]: https://github.com/felix-liuyj/base-fastapi-template/blob/master/LICENSE.txt