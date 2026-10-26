# Changelog

## [0.10.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.9.0...v0.10.0) (2026-10-26)


### Features

* **admin:** Workflow-Aktionen aus dem Django-Admin entfernen ([3972c9c](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/3972c9c2341445a2ceb8953dcb3933411e854fdc))
* **workflow:** Auslosung im Workflow-Tab zurücksetzen ([ac0cb85](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/ac0cb856d2d3d352455f7076ea0a277aab3eec95))
* **workflow:** Halbjahres-Workflow-Modul mit Phase und geschützten Aktionen ([03a3b7a](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/03a3b7a92488fc7024cbd2980f6aafec77a48509))


### Bug Fixes

* **emails:** veraltete Zuteilungsmail nicht als gesendet markieren ([5402ac7](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/5402ac7827f6e73c0867416fb7c84c1591f7c7c8))
* **emails:** Zusage unter der Halbjahressperre prüfen und markieren ([146f85d](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/146f85dd6d4ddae82a6b7b8b99793487d75bb095))
* **tasks:** Fehlermeldung nennt auch veraltete Zuteilungen ([1291796](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/1291796cb89d5b2948c5aa32855d41ea18d096e7))


### Performance Improvements

* **emails:** Bulk-Versand der vorläufigen Listen leitet die Phase einmal ab ([758a770](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/758a770328fbe70b48efa11a2061d0e4db0d7693))

## [0.9.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.8.0...v0.9.0) (2026-10-21)


### Features

* **admin:** AG-Leitung, Termine und Ort in der AG-Übersicht ([#138](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/138)) ([bdd9175](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/bdd9175a6b2a5981fdbbd325f9ea2ce84645d0f3))
* AG duplizieren ([#140](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/140)) ([281ae4d](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/281ae4ddf4e05c29bf10ce9dd73f97f1ae448f68)), closes [#132](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/132)
* AG im Portal bearbeiten ([#139](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/139)) ([f6f4cf5](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/f6f4cf5dc5910013f39e4745d96b5fe621b6b08a))
* Erinnerungsmail an AG-Teilnehmer vor dem Termin ([#137](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/137)) ([b8d9d76](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b8d9d76ee752ca01835c10d1251d09a05cb54c0a)), closes [#125](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/125)
* maximal 4 AG-Wahlen pro Kind ab dem nächsten Halbjahr ([#141](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/141)) ([cf6e29f](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/cf6e29f7b701efb02faf35c2f653e12827581691))
* vorläufige Teilnehmerliste an AG-Leiter ([#135](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/135)) ([d6a233e](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/d6a233e4832aab1c13fb546f35c3d917cf6c9803))
* Workflow-Tab im Admin-Bereich ([#136](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/136)) ([e322a40](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/e322a40637142b6460bca91fead31d0be0974608)), closes [#129](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/129)


### Bug Fixes

* **email:** E-Mail-Versand im Hintergrund mit Timeout und Wiederholung ([#134](https://github.com/ruben-sch/schul-ag-portal-gechingen/issues/134)) ([b0fb1d5](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b0fb1d5728bb7999654c79a1430e3d0c85d45e94))

## [0.8.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.7.0...v0.8.0) (2026-09-29)


### Features

* trigger for release ([3691140](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/3691140afa9c2274450a4c8e59403db17e79b311))

## [0.7.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.6.0...v0.7.0) (2026-09-27)


### Features

* add docker agent skills ([d2f4d86](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/d2f4d867e80af3332e262a32b88a55a23b55fbfa))
* enforce maximum limit of 5 AG selections and priority values between 1 and 5 ([dc41a0b](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/dc41a0bd38a6ea7320e2ad80fbb6090f328253b0))

## [0.6.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.5.0...v0.6.0) (2026-03-31)


### Features

* add contact details to stats export and format student lists as vertical blocks ([629370f](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/629370fcd2c9fd6b27589c7ef4b39bbc329c6691))

## [0.5.0](https://github.com/ruben-sch/schul-ag-portal-gechingen/compare/v0.4.0...v0.5.0) (2026-03-31)


### Features

* several improvements ([b7eb940](https://github.com/ruben-sch/schul-ag-portal-gechingen/commit/b7eb940d365341e62af22de9f1369977eb02fa22))

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
