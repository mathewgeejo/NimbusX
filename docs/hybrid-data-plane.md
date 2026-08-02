# Hybrid data-plane scaffold

NimbusX has a target hybrid model: hosted tenants run source adapters in
NimbusX-managed infrastructure, while private tenants keep provider
credentials, raw extracts, and sensitive asset context within their own VPC.

## What the supplied chart does today

`deploy/helm/nimbusx-data-plane` deploys a long-running, metadata-only mTLS
heartbeat process. It is outbound-only and mounts `tls.crt` and `tls.key` from
an existing Kubernetes Secret. Its heartbeat includes only the data-plane ID,
timestamp, and `raw_data_transfer: false`.

It does **not** claim jobs, process provider data, upload raw data, use an
outbound token, or return findings. Do not treat it as a customer data worker.
It mounts only mTLS material and contains no customer-artifact storage path.

This repository also does **not** implement the heartbeat receiver, server-side
mTLS policy, data-plane registration, replay protection, or enrollment API. An
operator must supply a separately reviewed HTTPS receiver; the chart merely
posts metadata to the configured exact URL.

## Installing the heartbeat scaffold

Build the supplied `docker/data-plane.Dockerfile`, publish it to a
customer-approved registry with an immutable digest, create an existing Secret
with `tls.crt` and `tls.key` keys using the customer secret manager/integration,
and then configure the exact HTTPS heartbeat endpoint and a non-secret
identifier:

```bash
helm upgrade --install nimbusx-private ./deploy/helm/nimbusx-data-plane \
  --set image.repository=registry.example/nimbusx-data-plane \
  --set image.digest=sha256:IMAGE_DIGEST \
  --set config.heartbeatUrl=https://control.example.com/v1/private/heartbeat \
  --set config.dataPlaneId=PLANE_IDENTIFIER \
  --set existingSecret=nimbusx-private-mtls
```

The chart defaults to a deny-all `NetworkPolicy`. Add only DNS and the exact
control-plane egress rule that the customer explicitly approves. With an empty
egress list, the pod is intentionally unable to reach the heartbeat endpoint
and remains unready. Its liveness probe checks process/configuration loading;
its readiness probe performs the metadata-only mTLS heartbeat.

## Required work before private analysis

A private analysis plane needs a signed and replay-protected job-claim protocol,
certificate rotation, custom-CA support where required, idempotency keys,
customer-owned encrypted object storage, artifact retention controls,
provider-specific rate limits, and an encrypted derived-finding/provenance
return contract. Those components are deliberately not simulated here.