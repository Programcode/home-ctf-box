# Attacker-side harness image: runs solvers inside the isolated lab
# network exactly like a learner workstation would.
FROM python:3.12-alpine
WORKDIR /work
COPY packages/content-sdk /sdk
RUN pip install --no-cache-dir --no-deps /sdk \
    && pip install --no-cache-dir httpx==0.28.1 pydantic==2.13.4 pyyaml==6.0.3 typer==0.27.1 rich==15.0.0 jsonschema==4.26.0 paramiko==4.0.0
ENV PYTHONPATH=/sdk/src:/bundle/solver
CMD ["python3"]
