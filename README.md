# E-Sim

This project uses Docker and Docker Compose for development and deployment.

## Prerequisites

Ensure you have the following installed on your system:
- [Git](https://git-scm.com/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Task](https://taskfile.dev/docs/installation)

## Getting Started

To initialize the project and start the application, run the following commands in the project root:

```bash
task
```

For more information;

```bash
task -l
```


## Server deployment

```bash
curl -O https://raw.githubusercontent.com/nbqduong/e-sim/main/scripts/deploy.sh
sh deploy.sh GITHUB_ACCESS_TOKEN
```
