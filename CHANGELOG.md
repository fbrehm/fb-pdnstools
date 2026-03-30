# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-03-30

### Changed

* Ensure build environment to create two Debian packages. 
* Setting the copyright year to 2026.

## [1.1.2] - 2026-02-24

### Changed

* Renamed directory `test` => `tests` to avoid confusion with git branch **test**.

## [1.1.1] - 2026-02-06

### Added

* Adding `ALIAS` as a valid Resource record type.

### Changed

* Non change release for triggering build pipelines.

## [1.1.0] - 2025-12-08

### Added

* Adding `CHANGELOG.md`.
* Adding `pyproject.toml`.

### Changed

* Cleaning up no more used stuff.
* Updating `update-env.sh` for refactored virtual env.
* Transforming `src/fb_pdnstools/bulk_rm_app.py into` an entrypoint.
* Applying black to all Python files.
* Updating Gitlab and Github CI workflows for the changes in build process.

### Removed

* Removed `bin/pdns-bulk-remove` - it's an entrypoint now.

### Fixed

*  Fixing `src/fb_vmware/xlate.py`.

## [1.0.2] - 2024-07-01

### Added

* Adding GitHub workflow build-packages for using a shared workflow.

### Changed

* Setting shared Github workflow to branch main.
* Updating dependencies to `fb_tools` >= 2.6.0.
* Disabling Github workflow packages.

## [1.0.0] - 2024-02-04

### Added

* Adding distros Debian 13 (trixie) and Ubuntu 24.04 (Noble Numbat) to
  Github workflow packages for building OS packages.

### Changed

* Updating .gitlab-ci.yml to use Python 3.12 for tests and linting.
* Using Python 3.12 for CI linter tests.
* Updating external Guthub actions.

### Removed

* Removing deprecated OS versions Ubuntu 18.04 (Bionic Beaver) and
  Enterprise Linux 7 from Github workflow.

## [0.6.1] - 2024-01-16

### Added

* Adding and using exception PDNSRequestError for exceptions
  originating from Python requests.

### Changed

* Simplyfication of init of some classes.
* Changing output of test scripts.

## [0.6.0] - 2023-07-20

### Added

* Adding requirements-lint.txt and using it for extended flake8 tests.
* Adding module `fb_pdnstools.common` for public function seconds2human().
* Adding human readable time properties to PowerDNSRecord.

### Changed

* Shifting class BasePowerDNSHandler into new module `fb_pdnstools.base_handler`.
* Applying flake8 rules to all python scripts and modules.

## [0.5.6] - 2022-12-30

### Added

* Adding signing of all Debian packages in Githaub workflow.

### Changed

* Updating package dependencies in template.spec and debian/control .
* Using shared pipelines in .gitlab-ci.yml.

## [0.5.5] - 2022-11-23

### Added

* Adding support for CentOS 9 in .gitlab-ci.yml

## [0.5.4] - 2022-11-21

### Added

* Adding rpm-addsign-wrapper.expect.

## [0.5.3] - 2022-11-21

### Added

* Adding tests for Python 3.11.
* Adding .gitlab-ci.yml.

### Changed

* Ensuring visibility of --simulate option.
* Renaming locale definitions `de_DE` => `de` and `en_US` => `en`.

## [0.5.2] - 2022-04-24

### Added

* Adding reinstallation of tzdata on building RPM packages.

## [0.5.1] - 2022-04-24

* Adding support for Ubuntu 22.04 Jammy Jellyfish.

## [0.5.0] - 2022-02-10

### Changed

* Support creating RPMs for CentOS Stream 9.
* Changing Distro for building EL-8 packages to CentOS Stream 8.

## [0.4.4] - 2021-12-07

### Added

* Adding properties `edited_serial`, `master_tsig_key_ids` and
  `slave_tsig_key_ids` to class PowerDNSZone.
* Extending test data for new properties of class PowerDNSZone.
* Adding class property `warn_on_unknown_property` to class
  PowerDNSZone to optional warn on new properties of a zone in the
  PowerDNS API.

## [0.4.3] - 2021-11-17

### Fixed

* Fixing `.github/workflows/packages.yaml`.

## [0.4.2] - 2021-11-17

### Fixed

* Fixing `.github/workflows/packages.yaml`.

## [0.4.1] - 2021-11-17

### Added

* Adding fb-pdnstools.spec.template and some helper scripts for
  creating RPM packages.
* Adding Github workflow and actions for a complete workchain for
  creating PyPi, Debian and RPM packages and deploying them.

## [0.4.0] - 2021-11-15

### Added

* Adding `lib/fb_pdnstools/record.py` for classes PowerDNSRecord,
  PowerDNSRecord and PowerDNSRecordList.
* Adding `lib/fb_pdnstools/zone.py` for classes PDNSNoRecordsToRemove,
  PowerDNSZone and PowerDNSZoneDict.
* Adding `lib/fb_pdnstools/server.py` for class PowerDNSServer.
* Adding `bin/pdns-bulk-remove`, `lib/fb_pdnstools/bulk_rm_app.py` and
  `lib/fb_pdnstools/bulk_rm_cfg.py` for an application to remove a bunch
  of addresses from PowerDNS.
* Adding tests for those new classes and modules.

## [0.3.0] - 2021-11-25

### Added

* Initial release.

[1.2.0]: https://github.com/fbrehm/fb-pdnstools/compare/1.1.2...1.2.0
[1.1.2]: https://github.com/fbrehm/fb-pdnstools/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/fbrehm/fb-pdnstools/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/fbrehm/fb-pdnstools/compare/1.0.2...1.1.0
[1.0.2]: https://github.com/fbrehm/fb-pdnstools/compare/1.0.0...1.0.2
[1.0.0]: https://github.com/fbrehm/fb-pdnstools/compare/0.6.1...1.0.0
[0.6.1]: https://github.com/fbrehm/fb-pdnstools/compare/0.6.0...0.6.1
[0.6.0]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.6...0.6.0
[0.5.6]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.5...0.5.6
[0.5.5]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.4...0.5.5
[0.5.4]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.3...0.5.4
[0.5.3]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.2...0.5.3
[0.5.2]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.1...0.5.2
[0.5.1]: https://github.com/fbrehm/fb-pdnstools/compare/0.5.0...0.5.1
[0.5.0]: https://github.com/fbrehm/fb-pdnstools/compare/0.4.4...0.5.0
[0.4.4]: https://github.com/fbrehm/fb-pdnstools/compare/0.4.3...0.4.4
[0.4.3]: https://github.com/fbrehm/fb-pdnstools/compare/0.4.2...0.4.3
[0.4.2]: https://github.com/fbrehm/fb-pdnstools/compare/0.4.1...0.4.2
[0.4.1]: https://github.com/fbrehm/fb-pdnstools/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/fbrehm/fb-pdnstools/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/fbrehm/fb-pdnstools/releases/tag/0.3.0

