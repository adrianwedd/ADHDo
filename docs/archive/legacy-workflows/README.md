# Retired legacy workflows

On 31 October 2026 the owner selected **ADHDo 2 only** as the supported product.
These files are preserved byte-for-byte from main at `d1c510c` and are outside
`.github/workflows`, so GitHub does not execute their triggers or schedules.

- `ci.yml`: old FastAPI package, tests, Docker build and dependency scanning.
- `accessibility-testing.yml`: old FastAPI web UI/browser suite.
- `security-hardening.yml`: old server's security/dependency validation jobs.
- `issue-grooming.yml`: analyser whose feature inventory targets the retired
  `src/` stack, not ADHDo 2. Its scheduled recommendations are retired too.
- `ci-complex.yml.backup`: already inactive historical workflow variant.

This is a support-scope change, not evidence that the legacy application passed
its tests. Prior failed runs and all implementation history remain available.
The supported workflow is `.github/workflows/adhdo2.yml`; it runs on every PR
and push to main. Managed CodeQL and Socket checks remain independent signals.
