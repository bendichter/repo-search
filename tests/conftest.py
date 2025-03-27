"""Test fixtures for repo-search."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_search.models import RepositoryInfo, DocumentChunk
from repo_search.github.repository import GitHubRepositoryFetcher
from repo_search.api.client import RepoSearchClient
from repo_search.search.engine import SearchEngine
from repo_search.database.chroma import ChromaVectorDatabase


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_repo_info():
    """Create a sample repository info."""
    return RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        url="https://github.com/test-owner/test-repo",
        commit_hash="abcd1234",
        num_files=5,
        num_chunks=10,
        download_successful=True,
        chunking_successful=True,
        embedding_successful=True,
        file_hashes={
            "README.md": "hash1",
            "src/main.py": "hash2",
            "src/utils.py": "hash3",
            "tests/test_main.py": "hash4",
            "tests/test_utils.py": "hash5",
        }
    )


@pytest.fixture
def sample_document_chunks(sample_repo_info):
    """Create sample document chunks for testing."""
    chunks = []
    repo_name = f"{sample_repo_info.owner}/{sample_repo_info.name}"
    
    # Chunk for README.md
    chunks.append(DocumentChunk(
        id=f"{repo_name}/README.md/1",
        repository=repo_name,
        content="# Test Repository\n\nThis is a test repository for testing.",
        metadata={
            "file_path": "README.md",
            "chunk_type": "text",
            "start_line": 1,
            "end_line": 3,
        }
    ))
    
    # Chunk for src/main.py
    chunks.append(DocumentChunk(
        id=f"{repo_name}/src/main.py/1",
        repository=repo_name,
        content="def main():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    main()",
        metadata={
            "file_path": "src/main.py",
            "chunk_type": "code",
            "start_line": 1,
            "end_line": 5,
        }
    ))
    
    # Chunk for src/utils.py
    chunks.append(DocumentChunk(
        id=f"{repo_name}/src/utils.py/1",
        repository=repo_name,
        content="def helper():\n    return 'Helper function'\n",
        metadata={
            "file_path": "src/utils.py",
            "chunk_type": "code",
            "start_line": 1,
            "end_line": 2,
        }
    ))
    
    return chunks


@pytest.fixture
def mock_github_fetcher():
    """Create a mock GitHub repository fetcher."""
    with patch('repo_search.github.repository.GitHubRepositoryFetcher') as mock:
        fetcher_instance = MagicMock()
        mock.return_value = fetcher_instance
        yield fetcher_instance


@pytest.fixture
def mock_chroma_db(sample_repo_info, sample_document_chunks):
    """Create a mock Chroma vector database."""
    with patch('repo_search.database.chroma.ChromaVectorDatabase') as mock:
        db_instance = MagicMock()
        
        # Configure the mock to return our sample data
        db_instance.get_repository.return_value = sample_repo_info
        db_instance.list_repositories.return_value = [sample_repo_info]
        db_instance.get_chunk.return_value = sample_document_chunks[0]
        
        mock.return_value = db_instance
        yield db_instance


@pytest.fixture
def mock_search_engine(mock_github_fetcher, mock_chroma_db):
    """Create a mock search engine."""
    with patch('repo_search.search.engine.SearchEngine') as mock:
        engine_instance = MagicMock()
        
        # Configure the mock to use our fetcher and db mocks
        engine_instance.repo_fetcher = mock_github_fetcher
        engine_instance.db = mock_chroma_db
        
        mock.return_value = engine_instance
        yield engine_instance
