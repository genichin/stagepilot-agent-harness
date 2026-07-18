# GitHub review enforcement activation

This repository declares accountable **roles** in `governance/sync-contract.yaml`. GitHub enforcement is intentionally not enabled until real organization, repository, and reviewer identities are approved.

## Activation input

Keep the approved identity map outside this repository when it is sensitive to organization structure. Its required shape is:

```yaml
roles:
  stagepilot-governance-reviewer: "@example-org/governance"
```

Values must be an actual GitHub `@user` or `@organization/team` identity; logical role names are rejected.

## Generate and activate

After approval, generate the provider file explicitly:

```bash
python3 scripts/render_codeowners.py \
  --identities /approved/path/github-identities.yaml \
  --output .github/CODEOWNERS
```

Review the generated diff, commit it, then configure the GitHub repository ruleset to require CODEOWNERS review for the protected branch. GitHub rulesets remain an external, approved repository-administration action; this script does not call GitHub APIs or change remote settings.

The generated mappings cover every `sources` and `dependents` path declared by the sync contract. Re-run the generator when contracts or approved identities change.
