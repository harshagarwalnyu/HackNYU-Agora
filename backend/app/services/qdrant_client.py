"""

Qdrant vector database client for storing and retrieving embeddings.
Manages student notes/materials and memory summaries.
"""

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self) -> None:
        """Initialize Qdrant service."""
        self.url = settings.qdrant_url
        self.api_key = settings.qdrant_api_key
        self.collection_notes = settings.qdrant_collection_notes
        self.collection_memory = settings.qdrant_collection_memory
        self.vector_size = settings.qdrant_vector_size
        self.client: Optional[QdrantClient] = None

        logger.debug(
            "QdrantService instantiated",
            extra={
                "url": self.url,
                "collection_notes": self.collection_notes,
                "collection_memory": self.collection_memory,
                "vector_size": self.vector_size,
            },
        )

    async def initialize(self) -> None:
        """Initialize Qdrant client and ensure collections exist."""
        try:
            logger.debug("Connecting to Qdrant...", extra={"url": self.url})

            if self.url == ":memory:":
                self.client = QdrantClient(location=":memory:", timeout=30)
            else:
                self.client = QdrantClient(url=self.url, api_key=self.api_key, timeout=30)

            logger.info("Qdrant client connected successfully")

            # Create collections if they don't exist
            await self._ensure_collection(self.collection_notes, "Student notes and materials")
            await self._ensure_collection(self.collection_memory, "Memory summaries")

            logger.info(
                "Qdrant initialization completed",
                extra={"collections": [self.collection_notes, self.collection_memory]},
            )

        except Exception as e:
            logger.error(
                "Failed to initialize Qdrant",
                extra={"error": str(e), "error_type": type(e).__name__, "url": self.url},
                exc_info=True,
            )
            raise

    async def close(self) -> None:
        """Close Qdrant client connection."""
        try:
            logger.debug("Closing Qdrant client...")
            if self.client:
                self.client.close()
            self.client = None
            logger.info("Qdrant client closed successfully")
        except Exception as e:
            logger.error(
                "Error closing Qdrant client",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )

    async def health_check(self) -> bool:
        """
        Check Qdrant health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            logger.debug("Checking Qdrant health...")

            if not self.client:
                logger.warning("Qdrant client not initialized")
                return False

            # Try to list collections
            collections = self.client.get_collections()
            is_healthy = collections is not None

            logger.debug(
                "Qdrant health check completed",
                extra={
                    "healthy": is_healthy,
                    "collections_count": len(collections.collections) if collections else 0,
                },
            )

            return is_healthy

        except Exception as e:
            logger.error(
                "Qdrant health check failed",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            return False

    async def _ensure_collection(self, collection_name: str, description: str) -> None:
        """
        Ensure a collection exists, create if it doesn't.

        Args:
            collection_name: Name of the collection
            description: Collection description
        """
        try:
            logger.debug(f"Checking if collection exists: {collection_name}")

            if not self.client:
                raise RuntimeError("Qdrant client not initialized")

            # Check if collection exists
            try:
                collection_info = self.client.get_collection(collection_name)
                logger.info(
                    f"Collection already exists: {collection_name}",
                    extra={
                        "points_count": collection_info.points_count,
                        "vectors_count": collection_info.vectors_count,
                    },
                )
                return
            except Exception as e:
                # If it's an UnexpectedResponse with 404, that's expected - we create it.
                # If it's something else, we log it but still try to create as a fallback.
                if isinstance(e, UnexpectedResponse) and e.status_code == 404:
                    logger.debug(f"Collection doesn't exist: {collection_name}, will create")
                else:
                    logger.warning(
                        f"Error checking collection {collection_name}, attempting to create anyway",
                        extra={"error": str(e)},
                    )

            # Create collection
            logger.info(
                f"Creating collection: {collection_name}",
                extra={"vector_size": self.vector_size, "distance": "Cosine"},
            )

            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size, distance=models.Distance.COSINE
                    ),
                )
                logger.info(f"Collection created successfully: {collection_name}")
            except UnexpectedResponse as e:
                if e.status_code == 409:
                    logger.info(f"Collection {collection_name} was created by another process")
                else:
                    raise

        except Exception as e:
            logger.error(
                f"Failed to ensure collection: {collection_name}",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise

    async def upsert_notes(
        self, user_id: str, course_id: str, chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Insert or update note chunks with embeddings.

        Args:
            user_id: User identifier
            course_id: Course/topic identifier
            chunks: List of chunk dictionaries with 'id', 'text', 'embedding', 'metadata'
        """
        try:
            logger.debug(
                "Upserting note chunks",
                extra={"user_id": user_id, "course_id": course_id, "chunks_count": len(chunks)},
            )

            if not self.client:
                raise RuntimeError("Qdrant client not initialized")

            if not chunks:
                logger.warning("No chunks to upsert")
                return

            # Build points
            points = []
            for chunk in chunks:
                point = models.PointStruct(
                    id=chunk["id"],
                    vector=chunk["embedding"],
                    payload={
                        "user_id": user_id,
                        "course_id": course_id,
                        "text": chunk["text"],
                        "metadata": chunk.get("metadata", {}),
                    },
                )
                points.append(point)

            logger.debug(f"Prepared {len(points)} points for upsert")

            # Upsert to Qdrant
            self.client.upsert(collection_name=self.collection_notes, points=points)

            logger.info(
                "Note chunks upserted successfully",
                extra={"user_id": user_id, "course_id": course_id, "points_upserted": len(points)},
            )

        except Exception as e:
            logger.error(
                "Failed to upsert notes",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "course_id": course_id,
                    "chunks_count": len(chunks),
                },
                exc_info=True,
            )
            raise

    async def search_notes(
        self,
        query_embedding: List[float],
        user_id: str,
        course_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant note chunks.

        Args:
            query_embedding: Query vector
            user_id: User identifier
            course_id: Optional course filter
            limit: Maximum results to return

        Returns:
            List of matching chunks with scores
        """
        try:
            logger.debug(
                "Searching notes",
                extra={
                    "user_id": user_id,
                    "course_id": course_id,
                    "limit": limit,
                    "embedding_dim": len(query_embedding),
                },
            )

            if not self.client:
                raise RuntimeError("Qdrant client not initialized")

            # Build filter
            must_conditions: List[Any] = [
                models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
            ]

            if course_id:
                must_conditions.append(
                    models.FieldCondition(key="course_id", match=models.MatchValue(value=course_id))
                )

            query_filter = models.Filter(must=must_conditions)

            logger.debug(
                "Executing Qdrant search...", extra={"filter_conditions": len(must_conditions)}
            )

            # Search
            results = self.client.search(
                collection_name=self.collection_notes,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
            )

            # Format results
            formatted_results = []
            for hit in results:
                formatted_results.append(
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "text": (hit.payload or {}).get("text", ""),
                        "metadata": (hit.payload or {}).get("metadata", {}),
                        "user_id": (hit.payload or {}).get("user_id"),
                        "course_id": (hit.payload or {}).get("course_id"),
                    }
                )

            logger.info(
                "Note search completed",
                extra={
                    "results_count": len(formatted_results),
                    "user_id": user_id,
                    "course_id": course_id,
                    "top_score": formatted_results[0]["score"] if formatted_results else None,
                },
            )

            return formatted_results

        except Exception as e:
            logger.error(
                "Note search failed",
                extra={"error": str(e), "error_type": type(e).__name__, "user_id": user_id},
                exc_info=True,
            )
            raise

    async def upsert_memory(
        self, user_id: str, session_id: str, memory_data: Dict[str, Any], embedding: List[float]
    ) -> None:
        """
        Insert or update memory summary.

        Args:
            user_id: User identifier
            session_id: Session identifier
            memory_data: Memory data (mastered/confused topics)
            embedding: Memory embedding vector
        """
        try:
            logger.debug(
                "Upserting memory",
                extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "memory_keys": list(memory_data.keys()),
                },
            )

            if not self.client:
                raise RuntimeError("Qdrant client not initialized")

            point_id = f"memory:{user_id}:{session_id}"

            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={"user_id": user_id, "session_id": session_id, "memory_data": memory_data},
            )

            self.client.upsert(collection_name=self.collection_memory, points=[point])

            logger.info(
                "Memory upserted successfully",
                extra={"user_id": user_id, "session_id": session_id, "point_id": point_id},
            )

        except Exception as e:
            logger.error(
                "Failed to upsert memory",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                exc_info=True,
            )
            raise

    async def get_memory(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent memory summaries for a user.

        Args:
            user_id: User identifier
            limit: Maximum memories to retrieve

        Returns:
            List of memory summaries
        """
        try:
            logger.debug("Retrieving memory", extra={"user_id": user_id, "limit": limit})

            if not self.client:
                raise RuntimeError("Qdrant client not initialized")

            # Scroll through memories for this user
            records, _ = self.client.scroll(
                collection_name=self.collection_memory,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
                    ]
                ),
                limit=limit,
            )

            memories = []
            for record in records:
                payload = record.payload or {}
                memories.append(
                    {
                        "session_id": payload.get("session_id"),
                        "memory_data": payload.get("memory_data", {}),
                    }
                )

            logger.info(
                "Memory retrieved successfully",
                extra={"user_id": user_id, "memories_count": len(memories)},
            )

            return memories

        except Exception as e:
            logger.error(
                "Failed to retrieve memory",
                extra={"error": str(e), "error_type": type(e).__name__, "user_id": user_id},
                exc_info=True,
            )
            raise


# Global singleton instance
qdrant_service = QdrantService()

logger.debug("Qdrant service singleton created")
