"""Integrity of the bundled data files (brief §12, AGENTS.md §6): loadable,
alphabetical, well-formed URLs, no nulls for the majors, generated docs fresh."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

from keyfleet.bundled import load_bundled, services_markdown

URL_RE = re.compile(r"^https?://\S+$")

#: Majors must have a researched passkey answer, never null (brief §7).
MAJOR_SERVICES = ("google", "microsoft", "apple", "github", "aws", "bitwarden")


class TestServicesData:
    def test_at_least_30_services(self):
        assert len(load_bundled().services) >= 30

    def test_alphabetical_by_id(self):
        ids = list(load_bundled().services)
        assert ids == sorted(ids), "services.yaml entries must stay alphabetical by id"

    def test_majors_have_non_null_passkey_answer(self):
        services = load_bundled().services
        for service_id in MAJOR_SERVICES:
            assert service_id in services, f"major service {service_id} missing"
            assert services[service_id].fido2_discoverable is not None, (
                f"{service_id}: fido2_discoverable must be researched, not null"
            )

    def test_urls_are_well_formed(self):
        for service_id, service in load_bundled().services.items():
            assert URL_RE.match(service.source_url), f"{service_id}: bad source_url"
            if service.security_settings_url is not None:
                assert URL_RE.match(service.security_settings_url), (
                    f"{service_id}: bad security_settings_url"
                )


class TestModelsData:
    def test_unique_ids_and_families(self):
        models = load_bundled().models
        ids = [info.id for info in models]
        assert len(ids) == len(set(ids))
        families = [(info.vendor, info.family.lower()) for info in models]
        assert len(families) == len(set(families))

    def test_every_entry_verified_with_source(self):
        for info in load_bundled().models:
            assert URL_RE.match(info.source_url), f"{info.id}: bad source_url"
            assert info.verified is not None


class TestAdvisoriesData:
    def test_unique_ids(self):
        ids = [advisory.id for advisory in load_bundled().advisories]
        assert len(ids) == len(set(ids))

    def test_each_advisory_bounded_and_linked(self):
        for advisory in load_bundled().advisories:
            affects = advisory.affects
            assert affects.firmware_lt or affects.firmware_ge, (
                f"{advisory.id}: affects needs at least one firmware bound"
            )
            assert URL_RE.match(advisory.url), f"{advisory.id}: bad url"
            assert advisory.verified is not None, f"{advisory.id}: missing verified date"


class TestExampleSync:
    def test_root_example_matches_packaged_copy(self):
        from keyfleet.bundled import example_ledger_text

        root = (REPO_ROOT / "keyfleet.example.yaml").read_text(encoding="utf-8")
        assert root == example_ledger_text(), (
            "keyfleet.example.yaml and src/keyfleet/data/example.yaml drifted — "
            "edit the root file and copy it into the package data"
        )


class TestGeneratedDocs:
    def test_services_md_is_fresh(self):
        path = REPO_ROOT / "docs" / "SERVICES.md"
        assert path.is_file(), "docs/SERVICES.md missing — run scripts/gen_services_md.py"
        assert path.read_text(encoding="utf-8") == services_markdown(load_bundled()), (
            "docs/SERVICES.md is stale — regenerate with: uv run python scripts/gen_services_md.py"
        )
