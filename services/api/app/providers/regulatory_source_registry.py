"""Registry of authoritative sources for VERA regulatory intelligence.

This registry defines source metadata and supported capabilities only.
It does not perform network requests or claim that a live verification
has occurred.
"""

from __future__ import annotations

from app.contracts.regulatory import (
    RegulatoryCapability,
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatorySourceKind,
)


class RegulatorySourceRegistry:
    """Manage approved regulatory source definitions."""

    def __init__(
        self,
        sources: list[RegulatorySource] | None = None,
    ) -> None:
        source_list = (
            sources
            if sources is not None
            else self._default_sources()
        )

        self._sources: dict[str, RegulatorySource] = {}

        for source in source_list:
            if source.source_id in self._sources:
                raise ValueError(
                    f"Duplicate regulatory source ID: "
                    f"{source.source_id}"
                )

            self._sources[source.source_id] = source

    @staticmethod
    def _default_sources() -> list[RegulatorySource]:
        """Return the initial authoritative source definitions."""

        return [
            RegulatorySource(
                source_id="sebi_investment_advisers",
                name="SEBI Investment Adviser Directory",
                authority="Securities and Exchange Board of India",
                url=(
                    "https://www.sebi.gov.in/sebiweb/other/"
                    "OtherAction.do?doRecognisedFpi=yes&intmId=13"
                ),
                kind=RegulatorySourceKind.REGULATOR,
                participant_types=(
                    RegulatoryParticipantType.INVESTMENT_ADVISER,
                ),
                capabilities=(
                    RegulatoryCapability.REGISTRATION_LOOKUP,
                    RegulatoryCapability.REGISTRATION_STATUS,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Official investment adviser directory. "
                    "A live lookup or authoritative record match "
                    "must be performed before reporting verification."
                ),
            ),
            RegulatorySource(
                source_id="sebi_research_analysts",
                name="SEBI Research Analyst Directory",
                authority="Securities and Exchange Board of India",
                url=(
                    "https://www.sebi.gov.in/sebiweb/other/"
                    "OtherAction.do?doRecognisedFpi=yes&intmId=14"
                ),
                kind=RegulatorySourceKind.REGULATOR,
                participant_types=(
                    RegulatoryParticipantType.RESEARCH_ANALYST,
                ),
                capabilities=(
                    RegulatoryCapability.REGISTRATION_LOOKUP,
                    RegulatoryCapability.REGISTRATION_STATUS,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Official research analyst directory. "
                    "Directory presence must not be interpreted as "
                    "proof that every claim made by the analyst is valid."
                ),
            ),
            RegulatorySource(
                source_id="nse_broker_locator",
                name="NSE Broker Locator",
                authority="National Stock Exchange of India",
                url=(
                    "https://enit.nseindia.com/MemDirWeb/"
                    "form/brokerLocator_beta.jsp"
                ),
                kind=RegulatorySourceKind.STOCK_EXCHANGE,
                participant_types=(
                    RegulatoryParticipantType.STOCKBROKER,
                    RegulatoryParticipantType.AUTHORISED_PERSON,
                ),
                capabilities=(
                    RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP,
                    RegulatoryCapability.AUTHORISED_PERSON_LOOKUP,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Official NSE member and authorised-person lookup. "
                    "The available record and membership scope must be "
                    "checked for the specific entity."
                ),
            ),
            RegulatorySource(
                source_id="bse_member_directory",
                name="BSE Member Directory",
                authority="BSE Limited",
                url=(
                    "https://www.bseindia.com/members/"
                    "MembershipDirectory.aspx"
                ),
                kind=RegulatorySourceKind.STOCK_EXCHANGE,
                participant_types=(
                    RegulatoryParticipantType.STOCKBROKER,
                ),
                capabilities=(
                    RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Official BSE member directory. "
                    "A directory listing does not by itself validate "
                    "an investment offer or impersonation claim."
                ),
            ),
            RegulatorySource(
                source_id="bse_enlisted_investment_advisers",
                name="BSE Enlisted Investment Advisers",
                authority="BSE Limited",
                url="https://www.bseindia.com/iara/IA_Member.aspx",
                kind=RegulatorySourceKind.STOCK_EXCHANGE,
                participant_types=(
                    RegulatoryParticipantType.INVESTMENT_ADVISER,
                ),
                capabilities=(
                    RegulatoryCapability.REGISTRATION_LOOKUP,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Exchange listing for investment advisers. "
                    "Enlistment and SEBI registration are distinct "
                    "fields and must not be conflated."
                ),
            ),
            RegulatorySource(
                source_id="bse_enlisted_research_analysts",
                name="BSE Enlisted Research Analysts",
                authority="BSE Limited",
                url="https://www.bseindia.com/IARA/RegisteredRA.aspx",
                kind=RegulatorySourceKind.STOCK_EXCHANGE,
                participant_types=(
                    RegulatoryParticipantType.RESEARCH_ANALYST,
                ),
                capabilities=(
                    RegulatoryCapability.REGISTRATION_LOOKUP,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                automated_access=False,
                notes=(
                    "Exchange listing for research analysts. "
                    "Use the source's actual fields and scope when "
                    "reporting a result."
                ),
            ),
        ]

    def list_sources(
        self,
        *,
        enabled_only: bool = True,
    ) -> list[RegulatorySource]:
        """List registered sources."""

        sources = list(self._sources.values())

        if enabled_only:
            sources = [
                source
                for source in sources
                if source.enabled
            ]

        return sorted(
            sources,
            key=lambda source: source.source_id,
        )

    def get_source(
        self,
        source_id: str,
    ) -> RegulatorySource | None:
        """Return a source by ID, or None if it is not registered."""

        return self._sources.get(source_id)

    def sources_for(
        self,
        participant_type: RegulatoryParticipantType,
        *,
        capability: RegulatoryCapability | None = None,
        enabled_only: bool = True,
    ) -> list[RegulatorySource]:
        """Find sources supporting a participant type and capability."""

        matching_sources = []

        for source in self._sources.values():
            if enabled_only and not source.enabled:
                continue

            if participant_type not in source.participant_types:
                continue

            if (
                capability is not None
                and capability not in source.capabilities
            ):
                continue

            matching_sources.append(source)

        return sorted(
            matching_sources,
            key=lambda source: source.source_id,
        )