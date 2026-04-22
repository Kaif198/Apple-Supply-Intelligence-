<!--
  ASCIIP PR template.
  Delete sections that don't apply, but keep the checklist — CI enforces most of it.
-->

## Summary

<!-- One paragraph: what does this PR change and why? -->

## Requirement coverage

- Closes #
- New / updated markers: `@pytest.mark.req_<N>` …

## Checklist

- [ ] Unit tests added or updated
- [ ] Integration / property test(s) updated if feature-store behaviour changed
- [ ] OpenAPI surface unchanged, or backend + frontend types regenerated
- [ ] Added / updated an ADR if an architectural choice changed
- [ ] `runbook.md` updated if the incident posture changed
- [ ] Screenshots attached for UI-visible changes

## Data-safety checks (required for any feature-store touching change)

- [ ] `pytest -m property` passes locally
- [ ] Added a new SQL view? Its header documents inputs / output / PIT key
- [ ] No sensitive values committed (run `gitleaks detect` locally if unsure)

## Deployment notes

<!-- Anything the on-call needs to do: env vars, migrations, feature flags, rollback steps. -->
