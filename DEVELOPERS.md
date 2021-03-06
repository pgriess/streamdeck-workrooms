# Releases

The general rule for releases is as follows.

- Major releases offer significant new functionality
- Minor releases offer minor new functionality or significant internal
  refactoring
- Patch releases are exclusively bug fixes

Release numbers are numbered `X.Y.Z`.

Release branches are named `release-vX.Y`.

Each release has a tag named `vX.Y.Z`.

The `CHANGELOG.md` file contains a developer-centric changelog of differences
since the last numerical version. That is, in the main branch this file should
have entries for all patch releases across all branches.

## How to create a release

Make sure that `CHANGELOG.md` is up to date.

Major and minor releases have their own branch. If this is the first version of
such a release, create a new branch for it.

```sh
git branch release-vX.Y HEAD
```

Create a tag for the release for the tip of the new branch.

```sh
git tag vX.Y.Z release-vX.Y
```

Make sure that `manifest.json` is updated to refer to the **next** release. For
new patch releases, this is only done in the branch. For new major or minor
releases, you wil need to go back to the `main` branch to do this. For example,
if you are shipping version 1.0.3, `manifest.json` in the branch should say
`1.0.4`.

Push all new refs to GitHub.

```sh
git push --all
git push --tags
```

Build a new release package

```sh
make plugin
```

Create a new release on GitHub by going to the
[releases](https://github.com/pgriess/streamdeck-workrooms/releases/) page,
filling out the form, and attaching the plugin built above. The text associated
with the release should include the release notes (probably from
`CHANGELOG.md`).

Send an email to to `streamdeck.elgato@corsair.com` with the following information

- Release notes. Probably cribbed from `CHANGELOG.md`, but filtered to be a
  bit more user-friendly.

- A link from which the new plugin can be downloaded. Binaries attached to
  GitHub releases can be downloaded without authentication.
