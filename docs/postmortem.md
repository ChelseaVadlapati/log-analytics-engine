# Postmortem: ARM vs AMD64 Docker deployment failure

**Date:** March 18, 2026
**Severity:** Low — deployment blocked for ~15 minutes
**Author:** Chelsea Vadlapati
**Status:** Resolved

## Summary

Cloud Run deployment failed immediately after `terraform apply` with the error:
`Container manifest type must support amd64/linux`.
The Docker image had been successfully built and pushed to Artifact Registry,
but Cloud Run rejected it at deployment time.

## Timeline

| Time | Event |
|------|-------|
| 02:10 | `terraform apply` started — 12 resources planned |
| 02:22 | Cloud SQL and Redis provisioned successfully |
| 02:23 | Cloud Run deployment failed with manifest type error |
| 02:25 | Root cause identified — ARM vs AMD64 mismatch |
| 02:27 | Image rebuilt with `--platform linux/amd64` flag |
| 02:30 | Image pushed and Cloud Run deployed successfully |
| 02:31 | Live URL confirmed working |

## Root cause

My MacBook has an Apple M-series chip (ARM64 architecture). Docker builds
images for the host architecture by default. The image was built as
`linux/arm64` but Cloud Run runs exclusively on `linux/amd64` infrastructure
and cannot execute ARM images.

The error message `application/vnd.oci.image.index.v1+json must support amd64/linux`
means the multi-platform manifest did not include an AMD64 variant.

## Resolution

Rebuilt the Docker image with an explicit platform target:
```bash
docker build --platform linux/amd64 \
  -f api/Dockerfile \
  -t us-central1-docker.pkg.dev/log-analytics-engine/log-analytics/api:latest \
  .
```

This cross-compiles the image for AMD64 regardless of the host machine architecture.

## What I'd do differently

Add the platform target to the Dockerfile itself so it's always explicit:
```dockerfile
FROM --platform=linux/amd64 python:3.11-slim
```

Or add it to the CI/CD pipeline build step so the correct architecture
is always used regardless of who runs the build. This is now documented
in the GitHub Actions workflow.

## Lessons learned

- Always specify `--platform linux/amd64` when building images intended
  for cloud deployment from Apple Silicon machines
- The error appears at deployment time, not at build or push time —
  Artifact Registry accepts any architecture, Cloud Run does not
- This is a common gotcha for any developer on Apple Silicon (M1/M2/M3)
  deploying to GCP, AWS, or Azure cloud infrastructure

## Impact

Zero user impact — this was caught during initial deployment before
any production traffic was routed to the service.