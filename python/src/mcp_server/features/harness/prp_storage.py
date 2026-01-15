"""
PRP (Project Requirements Plan) Storage Module

Stores PRPs in the RAG knowledge base so they survive context compaction
and are searchable via rag_search_knowledge_base().

PRPs are stored with:
- Source entry in archon_sources with source_id = prp_{project_id}
- Page(s) in archon_crawled_pages with embeddings
- URL pattern: archon://projects/{project_id}/prp
"""

import logging
from datetime import datetime
from urllib.parse import urljoin

import httpx

from src.mcp_server.utils.timeout_config import get_default_timeout
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)


def _generate_prp_source_id(project_id: str) -> str:
    """Generate a unique source_id for a project's PRP."""
    return f"prp_{project_id}"


def _generate_prp_url(project_id: str) -> str:
    """Generate the URL for a project's PRP."""
    return f"archon://projects/{project_id}/prp"


async def store_prp_in_rag(
    project_id: str,
    project_title: str,
    specification: str,
) -> dict:
    """
    Store a PRP (specification) in the RAG knowledge base.

    This creates:
    1. A source entry in archon_sources
    2. A page with embedding in archon_crawled_pages

    Args:
        project_id: UUID of the project
        project_title: Title of the project
        specification: The PRP/specification text to store

    Returns:
        dict with success status and details
    """
    try:
        source_id = _generate_prp_source_id(project_id)
        prp_url = _generate_prp_url(project_id)

        logger.info(f"Storing PRP in RAG for project {project_id}")

        # Use the internal API to store the document
        # This leverages the existing document storage infrastructure
        api_url = get_api_url()
        timeout = get_default_timeout()

        async with httpx.AsyncClient(timeout=timeout) as client:
            # First, create or update the source entry
            source_data = {
                "source_id": source_id,
                "title": f"PRP: {project_title}",
                "summary": specification[:500] + "..." if len(specification) > 500 else specification,
                "total_word_count": len(specification.split()),
                "metadata": {
                    "knowledge_type": "prp",
                    "project_id": project_id,
                    "project_title": project_title,
                    "source_type": "prp",
                    "tags": ["prp", "specification", "requirements"],
                    "created_at": datetime.utcnow().isoformat(),
                },
                "source_url": prp_url,
                "source_display_name": f"{project_title} - PRP",
            }

            # Upsert the source
            source_response = await client.post(
                urljoin(api_url, "/api/internal/prp/source"),
                json=source_data,
            )

            if source_response.status_code not in (200, 201):
                # Try direct database insert as fallback
                logger.warning(f"PRP source endpoint not available, using fallback: {source_response.status_code}")
                return await _store_prp_fallback(project_id, project_title, specification)

            # Now store the document content with embedding
            page_data = {
                "source_id": source_id,
                "url": prp_url,
                "content": specification,
                "metadata": {
                    "project_id": project_id,
                    "document_type": "prp",
                    "title": f"PRP: {project_title}",
                },
            }

            page_response = await client.post(
                urljoin(api_url, "/api/internal/prp/page"),
                json=page_data,
            )

            if page_response.status_code not in (200, 201):
                logger.warning(f"PRP page endpoint not available, using fallback: {page_response.status_code}")
                return await _store_prp_fallback(project_id, project_title, specification)

            return {
                "success": True,
                "source_id": source_id,
                "url": prp_url,
                "message": f"PRP stored in RAG for project {project_id}",
            }

    except Exception as e:
        logger.error(f"Error storing PRP in RAG: {e}", exc_info=True)
        # Try fallback method
        try:
            return await _store_prp_fallback(project_id, project_title, specification)
        except Exception as fallback_error:
            logger.error(f"Fallback PRP storage also failed: {fallback_error}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store PRP in RAG",
            }


async def _store_prp_fallback(
    project_id: str,
    project_title: str,
    specification: str,
) -> dict:
    """
    Fallback method to store PRP directly in the database.

    This bypasses the HTTP API and uses direct database operations.
    """
    try:
        from src.server.utils import get_supabase_client
        from src.server.services.embeddings.embedding_service import create_embedding

        supabase = get_supabase_client()
        source_id = _generate_prp_source_id(project_id)
        prp_url = _generate_prp_url(project_id)

        logger.info(f"Using fallback method to store PRP for project {project_id}")

        # Create embedding for the specification
        embedding = await create_embedding(specification)

        # Upsert the source entry
        source_data = {
            "source_id": source_id,
            "title": f"PRP: {project_title}",
            "summary": specification[:500] + "..." if len(specification) > 500 else specification,
            "total_word_count": len(specification.split()),
            "metadata": {
                "knowledge_type": "prp",
                "project_id": project_id,
                "project_title": project_title,
                "source_type": "prp",
                "tags": ["prp", "specification", "requirements"],
            },
            "source_url": prp_url,
            "source_display_name": f"{project_title} - PRP",
        }

        supabase.table("archon_sources").upsert(source_data).execute()

        # Delete any existing page for this URL (to handle updates)
        supabase.table("archon_crawled_pages").delete().eq("url", prp_url).execute()

        # Insert the page with embedding
        page_data = {
            "source_id": source_id,
            "url": prp_url,
            "content": specification,
            "embedding": embedding,
            "metadata": {
                "project_id": project_id,
                "document_type": "prp",
                "title": f"PRP: {project_title}",
                "knowledge_type": "prp",
            },
        }

        supabase.table("archon_crawled_pages").insert(page_data).execute()

        logger.info(f"Successfully stored PRP in RAG via fallback for project {project_id}")

        return {
            "success": True,
            "source_id": source_id,
            "url": prp_url,
            "message": f"PRP stored in RAG for project {project_id}",
            "method": "fallback",
        }

    except Exception as e:
        logger.error(f"Fallback PRP storage failed: {e}", exc_info=True)
        raise


async def retrieve_prp_for_project(project_id: str) -> dict:
    """
    Retrieve the PRP for a project from the RAG knowledge base.

    Args:
        project_id: UUID of the project

    Returns:
        dict with success status and PRP content
    """
    try:
        from src.server.utils import get_supabase_client

        supabase = get_supabase_client()
        source_id = _generate_prp_source_id(project_id)
        prp_url = _generate_prp_url(project_id)

        # Try to get the page directly by URL
        response = (
            supabase.table("archon_crawled_pages")
            .select("content, metadata")
            .eq("url", prp_url)
            .execute()
        )

        if response.data and len(response.data) > 0:
            page = response.data[0]
            return {
                "success": True,
                "content": page.get("content", ""),
                "metadata": page.get("metadata", {}),
                "source_id": source_id,
                "url": prp_url,
            }

        # Fallback: try to get by source_id
        response = (
            supabase.table("archon_crawled_pages")
            .select("content, metadata, url")
            .eq("source_id", source_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            page = response.data[0]
            return {
                "success": True,
                "content": page.get("content", ""),
                "metadata": page.get("metadata", {}),
                "source_id": source_id,
                "url": page.get("url", prp_url),
            }

        return {
            "success": False,
            "error": f"No PRP found for project {project_id}",
            "message": "PRP not found in RAG",
        }

    except Exception as e:
        logger.error(f"Error retrieving PRP from RAG: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve PRP from RAG",
        }


async def delete_prp_for_project(project_id: str) -> dict:
    """
    Delete the PRP for a project from the RAG knowledge base.

    Args:
        project_id: UUID of the project

    Returns:
        dict with success status
    """
    try:
        from src.server.utils import get_supabase_client

        supabase = get_supabase_client()
        source_id = _generate_prp_source_id(project_id)
        prp_url = _generate_prp_url(project_id)

        # Delete the page
        supabase.table("archon_crawled_pages").delete().eq("url", prp_url).execute()

        # Delete the source
        supabase.table("archon_sources").delete().eq("source_id", source_id).execute()

        logger.info(f"Deleted PRP from RAG for project {project_id}")

        return {
            "success": True,
            "source_id": source_id,
            "message": f"PRP deleted from RAG for project {project_id}",
        }

    except Exception as e:
        logger.error(f"Error deleting PRP from RAG: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to delete PRP from RAG",
        }
