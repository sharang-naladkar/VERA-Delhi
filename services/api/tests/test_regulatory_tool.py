"""Tests for the regulatory knowledge investigation tool."""

from uuid import uuid4

import pytest

from app.contracts.regulatory import RegulatorySearchResponse
from app.contracts.status import AnalysisStatus
from app.investigator.tools.regulatory_tool import RegulatoryKnowledgeTool
from app.providers.regulatory import (
    MockRegulatoryKnowledgeProvider,
    UnavailableRegulatoryKnowledgeProvider,
)


@pytest.mark.asyncio
async def test_regulatory_tool_missing_query() -> None:
    tool = RegulatoryKnowledgeTool(
        MockRegulatoryKnowledgeProvider()
    )

    result = await tool.execute({})

    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == []
    assert result.output_data["results"] == []


@pytest.mark.asyncio
async def test_regulatory_tool_unavailable_provider() -> None:
    tool = RegulatoryKnowledgeTool(
        UnavailableRegulatoryKnowledgeProvider()
    )

    result = await tool.execute(
        {
            "investigation_id": str(uuid4()),
            "regulatory_query": (
                "investment adviser registration requirements"
            ),
        }
    )

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert len(result.evidence) == 1
    assert result.evidence[0].status == AnalysisStatus.UNAVAILABLE
    assert result.output_data["results"] == []
    assert result.output_data["source_available"] is False


@pytest.mark.asyncio
async def test_regulatory_tool_mock_provider() -> None:
    tool = RegulatoryKnowledgeTool(
        MockRegulatoryKnowledgeProvider()
    )

    result = await tool.execute(
        {
            "regulatory_query": "investment adviser registration requirements",
            "top_k": 5,
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert len(result.evidence) == 1
    assert result.evidence[0].status == AnalysisStatus.SUCCESS
    assert result.output_data["status"] == AnalysisStatus.SUCCESS.value
    assert result.output_data["source_available"] is True
    assert result.output_data["results"] == []


@pytest.mark.asyncio
async def test_regulatory_tool_accepts_query_alias() -> None:
    tool = RegulatoryKnowledgeTool(
        MockRegulatoryKnowledgeProvider()
    )

    result = await tool.execute(
        {
            "query": "SEBI investment adviser regulations",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert result.output_data["query"] == (
        "SEBI investment adviser regulations"
    )


@pytest.mark.asyncio
async def test_regulatory_tool_limits_top_k() -> None:
    tool = RegulatoryKnowledgeTool(
        MockRegulatoryKnowledgeProvider()
    )

    result = await tool.execute(
        {
            "regulatory_query": "SEBI regulations",
            "top_k": 100,
        }
    )

    assert result.status == AnalysisStatus.SUCCESS


@pytest.mark.asyncio
async def test_regulatory_tool_preserves_response_contract() -> None:
    response = RegulatorySearchResponse(
        query="test regulatory query",
        results=[],
        source_available=True,
        status=AnalysisStatus.SUCCESS.value,
        metadata={
            "test_fixture": True,
        },
    )

    provider = MockRegulatoryKnowledgeProvider(response=response)
    tool = RegulatoryKnowledgeTool(provider)

    result = await tool.execute(
        {
            "regulatory_query": "test regulatory query",
        }
    )

    assert result.status == AnalysisStatus.SUCCESS
    assert result.output_data["query"] == "test regulatory query"
    assert result.output_data["source_available"] is True
    assert result.output_data["metadata"]["test_fixture"] is True