# Contributing

This is a security research project, not a general-purpose library. I'm not actively seeking contributions, but I welcome bug fixes and meaningful documentation improvements.

## What I'll Accept

- **Bug fixes** with clear reproduction steps
- **Documentation improvements** that add real value (not cosmetic rewording)
- **Test improvements** that catch real bugs

## What I Won't Accept

- AI-generated slop PRs (auto-generated refactors, mass linting, vague "improvements")
- Large PRs without prior discussion
- New features without reaching out first
- Cosmetic-only changes

## Before Submitting a PR

1. **Reach out first** for anything beyond a small bug fix. Contact the maintainer:
   - Twitter/X: [@kmcquade3](https://x.com/kmcquade3)
   - Cloud Security Forum Slack: Kinnaird McQuade
2. Fork the repo and create a feature branch
3. Make sure all tests pass: `cd attacker-infra && make test`
4. No secrets, credentials, or account IDs in commits
5. One PR per issue/fix
6. Write a clear description explaining **what** and **why**, with screenshots where applicable

## Setup

```bash
git clone https://github.com/BeyondTrust/agentcore-sandbox-breakout.git
cd agentcore-sandbox-breakout/attacker-infra
make setup
make test
```

## Commit Messages

```
fix: Handle chunk retry returning 0.0.0.0 in DNS server
docs: Add VPC mode mitigation steps to README
test: Add integration test for multi-session handling
```

## Ideas for Separate Projects

If you're interested in building a generic multi-tenant DNS exfiltration server (not scoped to this repo), reach out to the maintainer directly. Happy to discuss.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
