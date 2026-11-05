# Security Policy

## Supported versions

Only the latest [release](https://github.com/d1rty-pixel/ingetrazo-newton/releases) of Newton receives security fixes.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private reporting instead: [Report a vulnerability](https://github.com/d1rty-pixel/ingetrazo-newton/security/advisories/new) (Security tab of this repository).

Include the Newton version, the IngeTrazo version, your operating system and steps to reproduce. A minimal `.igz` file helps if the problem depends on a model.

You get a first response within 7 days. Fixes are released first; the advisory is published afterwards.

## Scope

In scope:

- the `newton/` extension, including the simulation worker process and its protocol;
- `runtime_setup.py` (downloads and hash verification of `uv` and MuJoCo, creation of the runtime);
- loading of Newton data stored in `.igz` files (`group.ext["newton"]`);
- `scripts/package.py` and the release zip.

Out of scope:

- vulnerabilities in IngeTrazo, MuJoCo, uv or Python themselves; please report those upstream;
- issues that require local code execution as the same user, since the extension runs with that user's rights anyway.
