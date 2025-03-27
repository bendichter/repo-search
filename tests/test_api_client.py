"""Tests for the API client module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from repo_search.api.client import RepoSearchClient
from repo_search.models import RepositoryInfo, SearchResult


class TestRepoSearchClient:
    """Test the RepoSearchClient class."""

    def test_initialization(self):
        """Test client initialization with default values."""
        with patch('repo_search.api.client.SearchEngine') as mock_engine:
            client = RepoSearchClient()
            mock_engine.assert_called_once()
            assert client.engine == mock_engine.return_value

    def test_initialization_with_params(self):
        """Test client initialization with custom parameters."""
        with patch('repo_search.api.client.SearchEngine') as mock_engine:
            client = RepoSearchClient(
                db_path=Path("/tmp/test_db"),
                api_key="test-api-key",
                token="test-token"
            )
            mock_engine.assert_called_once_with(
                db_path=Path("/tmp/test_db"),
                api_key="test-api-key",
                token="test-token"
            )
            assert client.engine == mock_engine.return_value

    def test_index_repository(self, mock_search_engine, sample_repo_info):
        """Test indexing a repository."""
        mock_search_engine.index_repository.return_value = sample_repo_info
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.index_repository("test-owner/test-repo")
        
        mock_search_engine.index_repository.assert_called_once_with(
            "test-owner/test-repo",
            force_refresh=False,
            force_redownload=False,
            force_rechunk=False,
            force_reembed=False
        )
        
        assert result == sample_repo_info
        assert result.owner == "test-owner"
        assert result.name == "test-repo"

    def test_index_repository_with_force_options(self, mock_search_engine, sample_repo_info):
        """Test indexing a repository with force options."""
        mock_search_engine.index_repository.return_value = sample_repo_info
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.index_repository(
            "test-owner/test-repo",
            force_refresh=True,
            force_redownload=True,
            force_rechunk=True,
            force_reembed=True
        )
        
        mock_search_engine.index_repository.assert_called_once_with(
            "test-owner/test-repo",
            force_refresh=True,
            force_redownload=True,
            force_rechunk=True,
            force_reembed=True
        )
        
        assert result == sample_repo_info

    def test_semantic_search(self, mock_search_engine, sample_document_chunks):
        """Test semantic search functionality."""
        # Create some search results
        search_results = [
            SearchResult(chunk=chunk, score=0.9) for chunk in sample_document_chunks
        ]
        
        mock_search_engine.search.return_value = search_results
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        results = client.semantic_search(
            query="test query",
            repository="test-owner/test-repo",
            limit=5,
            score_threshold=0.7
        )
        
        mock_search_engine.search.assert_called_once_with(
            "test query", 
            "test-owner/test-repo", 
            5, 
            0.7
        )
        
        assert results == search_results
        assert len(results) == len(sample_document_chunks)
        assert all(isinstance(result, SearchResult) for result in results)

    def test_get_repository(self, mock_search_engine, sample_repo_info):
        """Test getting repository information."""
        mock_search_engine.get_repository.return_value = sample_repo_info
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.get_repository("test-owner/test-repo")
        
        mock_search_engine.get_repository.assert_called_once_with("test-owner/test-repo")
        assert result == sample_repo_info

    def test_get_repository_not_found(self, mock_search_engine):
        """Test getting repository information when the repository is not found."""
        mock_search_engine.get_repository.return_value = None
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.get_repository("test-owner/test-repo")
        
        mock_search_engine.get_repository.assert_called_once_with("test-owner/test-repo")
        assert result is None

    def test_list_repositories(self, mock_search_engine, sample_repo_info):
        """Test listing all indexed repositories."""
        mock_search_engine.get_repositories.return_value = [sample_repo_info]
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        results = client.list_repositories()
        
        mock_search_engine.get_repositories.assert_called_once()
        assert len(results) == 1
        assert results[0] == sample_repo_info

    def test_delete_repository(self, mock_search_engine):
        """Test deleting a repository."""
        mock_search_engine.delete_repository.return_value = True
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.delete_repository("test-owner/test-repo")
        
        mock_search_engine.delete_repository.assert_called_once_with("test-owner/test-repo")
        assert result is True

    def test_delete_repository_not_found(self, mock_search_engine):
        """Test deleting a repository that is not found."""
        mock_search_engine.delete_repository.return_value = False
        
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        result = client.delete_repository("test-owner/test-repo")
        
        mock_search_engine.delete_repository.assert_called_once_with("test-owner/test-repo")
        assert result is False

    def test_clear(self, mock_search_engine):
        """Test clearing all data from the index."""
        client = RepoSearchClient()
        client.engine = mock_search_engine
        
        client.clear()
        
        mock_search_engine.clear.assert_called_once()
