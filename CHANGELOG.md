# Changelog

## [0.4.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.3.0...v0.4.0) (2026-03-17)


### Features

* **emails:** add tracking and manual resend capability for allocation emails ([b5b668f](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b5b668fffb37796e8703b640cca1382cb6237c22))
* **emails:** add tracking and resend capability for AG leader emails ([4fb2852](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/4fb2852e26aaafc77c9f8ea7897382c53def501d))
* **ui:** improve manual intervention view with search and inline priority editing ([6038c4d](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/6038c4dbe89c031fb19085e80e139535f771c1e5))


### Bug Fixes

* **reliability:** add transaction safety and better email-send feedback ([53ce3a6](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/53ce3a6217790f949132b3c987ef12ecd4107c3f))


### Performance Improvements

* **lottery:** eliminate O(N²) DB queries in Phase 2 of lottery algorithm ([b0aed4a](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b0aed4a618e434c38f3f907fce02736101a29f8a))

## [0.3.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.2.1...v0.3.0) (2026-03-17)


### Features

* helles email layout ([8e4cd50](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/8e4cd508b15801d6cca0b0d0fee7120677301c32))


### Bug Fixes

* Convert selected AG checkboxes to ordered hidden inputs on form submission to preserve priority. ([cdacfb1](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/cdacfb1d306f61655b3a83f982f44bb3170bee16))

## [0.2.1](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.2.0...v0.2.1) (2026-03-03)


### Bug Fixes

* Add packages write permission to release-please ([b124be1](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b124be1c97e46c993e2e4cb6dc8042a8a75d7544))
* trigger deploy-hetzner on release ([0dd3185](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/0dd3185c141db7ac32ac1222214b829269b41e62))

## [0.2.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.1.0...v0.2.0) (2026-03-03)


### Features

* Add CSV export function for flyer generation ([a874c32](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/a874c323f4eadb10543f6f265967d4600cca2e6f))
* Add immediate email confirmation for AG registration ([69e8783](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/69e8783e8173e50a4fe757060ba1ca1dd81ed920))
* Add logo to PDFs, dot-fill Ausgaben and attach participant lists as PDF ([67b2ac2](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/67b2ac29f6df9fb5bf55de2543ed43d86d06582e))
* Add Release Please GitHub Action ([efb73b3](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/efb73b317a5e52ab2827c247524a907d71e883fd))
* Display all AG properties in leader dashboard ([fb9aad8](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/fb9aad802cb177c2ac6010facee429b8b19fd591))
* Hinweis Absage in TN Emails ([0a44562](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/0a44562b5bbf20ca603adf092741256c0ce7e2d0))
* Hinweis Absage in TN Emails ([61d916b](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/61d916ba8fa71956516d1b08d4c320a35fea5e51))
* Implement Abrechnungsvordruck attachment via EmailMultiAlternatives ([e6900fb](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/e6900fbeb77589a3d7909c84e90b467c1ab9d242))


### Bug Fixes

* Generate Abrechnungsvordruck as PDF instead of CSV ([006fdd6](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/006fdd66dca9d7df7d863654955a6d6563850d18))
* Resolve Bandit B110 try-except-pass warning ([0010fc6](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/0010fc6ae0c3c17c2a3699e0f0a9ccc7b0a058e4))
