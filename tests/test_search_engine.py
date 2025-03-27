"""Tests for the search engine module."""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime
from pathlib import Path

from repo_search.models import RepositoryInfo, DocumentChunk, SearchResult
from repo_search.search.engine import SearchEngine


class TestSearchEngine:
    """Test the SearchEngine class."""

    def test_initialization_default(self):
        """Test search engine initialization with default values."""
        with patch('repo_search.search.engine.OpenAIEmbedder') as mock_embedder, \
             patch('repo_search.search.engine.ChromaVectorDatabase') as mock_db, \
             patch('repo_search.search.engine.GitHubRepositoryFetcher') as mock_fetcher, \
             patch('repo_search.search.engine.RepositoryChunker') as mock_chunker, \
             patch('repo_search.search.engine.config') as mock_config:
            
            # Configure mock config
            mock_config.db_path = Path("/mock/db/path")
            mock_config.openai_api_key = "mock-api-key"
            mock_config.github_token = "mock-github-token"
            
            # Initialize the search engine
            engine = SearchEngine()
            
            # Verify that components were initialized with the correct parameters
            mock_embedder.assert_called_once_with(api_key="mock-api-key")
            mock_db.assert_called_once_with(db_path=Path("/mock/db/path"), embedder=mock_embedder.return_value)
            mock_fetcher.assert_called_once_with(token="mock-github-token")
            mock_chunker.assert_called_once()
            
            # Verify that components were assigned correctly
            assert engine.db_path == Path("/mock/db/path")
            assert engine.api_key == "mock-api-key"
            assert engine.token == "mock-github-token"
            assert engine.embedder == mock_embedder.return_value
            assert engine.db == mock_db.return_value
            assert engine.repo_fetcher == mock_fetcher.return_value
            assert engine.chunker == mock_chunker.return_value

    def test_initialization_custom(self):
        """Test search engine initialization with custom parameters."""
        with patch('repo_search.search.engine.OpenAIEmbedder') as mock_embedder, \
             patch('repo_search.search.engine.ChromaVectorDatabase') as mock_db, \
             patch('repo_search.search.engine.GitHubRepositoryFetcher') as mock_fetcher, \
             patch('repo_search.search.engine.RepositoryChunker') as mock_chunker:
            
            # Initialize the search engine with custom parameters
            engine = SearchEngine(
                db_path=Path("/custom/db/path"),
                api_key="custom-api-key",
                token="custom-github-token"
            )
            
            # Verify that components were initialized with the correct parameters
            mock_embedder.assert_called_once_with(api_key="custom-api-key")
            mock_db.assert_called_once_with(db_path=Path("/custom/db/path"), embedder=mock_embedder.return_value)
            mock_fetcher.assert_called_once_with(token="custom-github-token")
            mock_chunker.assert_called_once()
            
            # Verify that components were assigned correctly
            assert engine.db_path == Path("/custom/db/path")
            assert engine.api_key == "custom-api-key"
            assert engine.token == "custom-github-token"
            assert engine.embedder == mock_embedder.return_value
            assert engine.db == mock_db.return_value
            assert engine.repo_fetcher == mock_fetcher.return_value
            assert engine.chunker == mock_chunker.return_value

    def test_get_repository(self, mock_chroma_db, sample_repo_info):
        """Test getting repository information."""
        mock_chroma_db.get_repository.return_value = sample_repo_info
        
        engine = SearchEngine()
        engine.db = mock_chroma_db
        
        result = engine.get_repository("test-owner/test-repo")
        
        mock_chroma_db.get_repository.assert_called_once_with("test-owner/test-repo")
        assert result == sample_repo_info

    def test_get_repositories(self, mock_chroma_db, sample_repo_info):
        """Test getting all repositories."""
        mock_chroma_db.list_repositories.return_value = [sample_repo_info]
        
        engine = SearchEngine()
        engine.db = mock_chroma_db
        
        result = engine.get_repositories()
        
        mock_chroma_db.list_repositories.assert_called_once()
        assert len(result) == 1
        assert result[0] == sample_repo_info

    def test_delete_repository(self, mock_chroma_db):
        """Test deleting a repository."""
        mock_chroma_db.delete_repository.return_value = True
        
        engine = SearchEngine()
        engine.db = mock_chroma_db
        
        result = engine.delete_repository("test-owner/test-repo")
        
        mock_chroma_db.delete_repository.assert_called_once_with("test-owner/test-repo")
        assert result is True

    def test_clear(self, mock_chroma_db):
        """Test clearing all data."""
        engine = SearchEngine()
        engine.db = mock_chroma_db
        
        engine.clear()
        
        mock_chroma_db.clear.assert_called_once()

    def test_search(self, mock_chroma_db, mock_github_fetcher, sample_document_chunks):
        """Test searching for documents."""
        # Create search results from sample chunks
        search_results = [SearchResult(chunk=chunk, score=0.9) for chunk in sample_document_chunks]
        mock_chroma_db.search.return_value = search_results
        
        with patch('repo_search.search.engine.config') as mock_config, \
             patch('repo_search.search.engine.GitHubRepositoryFetcher') as mock_fetcher_class:
            # Configure mock config
            mock_config.max_results = 10
            mock_config.score_threshold = 0.5
            mock_config.github_token = "mock-token"
            
            # Return our mock fetcher when GitHubRepositoryFetcher is instantiated
            mock_fetcher_class.return_value = mock_github_fetcher
            
            engine = SearchEngine()
            engine.db = mock_chroma_db
            
            # Test with default parameters
            result_default = engine.search("test query")
            mock_chroma_db.search.assert_called_with("test query", None, 10, 0.5)
            assert result_default == search_results
            
            # Test with explicit parameters
            result_explicit = engine.search(
                "test query",
                repository="test-owner/test-repo",
                limit=5,
                score_threshold=0.7
            )
            mock_chroma_db.search.assert_called_with("test query", "test-owner/test-repo", 5, 0.7)
            assert result_explicit == search_results

    @pytest.mark.parametrize("force_refresh,force_redownload,force_rechunk,force_reembed", [
        (False, False, False, False),  # No force options
        (True, True, True, True),      # All force options
        (False, True, False, True),    # Mixed force options
    ])
    def test_index_repository_new(self, mock_github_fetcher, mock_chroma_db, temp_dir, 
                                force_refresh, force_redownload, force_rechunk, force_reembed):
        """Test indexing a new repository."""
        # Mock repository info from GitHub
        repo_info = RepositoryInfo(
            owner="test-owner",
            name="test-repo",
            url="https://github.com/test-owner/test-repo",
            commit_hash="abcd1234"
        )
        mock_github_fetcher.get_repository_info.return_value = repo_info
        
        # Mock fetch repository contents
        repo_path = temp_dir / "test-repo"
        mock_github_fetcher.fetch_repository_contents.return_value = (repo_info, repo_path)
        
        # Mock empty repository list (new repository)
        mock_chroma_db.get_repository.return_value = None
        
        with patch('repo_search.search.engine.RepositoryChunker') as mock_chunker_class, \
             patch('tempfile.mkdtemp') as mock_mkdtemp, \
             patch('shutil.rmtree') as mock_rmtree:
            
            # Mock chunker
            mock_chunker = MagicMock()
            mock_chunker_class.return_value = mock_chunker
            
            # Create some sample chunks
            sample_chunks = [
                DocumentChunk(
                    id=f"test-owner/test-repo/README.md/1",
                    repository="test-owner/test-repo",
                    content="# Test Repository\n\nThis is a test repository for testing.",
                    metadata={
                        "file_path": "README.md",
                        "chunk_type": "text",
                        "start_line": 1,
                        "end_line": 3,
                    }
                )
            ]
            
            # Mock chunking to return our sample chunks
            mock_chunker.chunk_repository.return_value = sample_chunks
            
            # Mock temp directory
            mock_mkdtemp.return_value = str(temp_dir)
            
            # Initialize the search engine with our mocks
            engine = SearchEngine()
            engine.repo_fetcher = mock_github_fetcher
            engine.db = mock_chroma_db
            engine.chunker = mock_chunker
            
            # Call the method under test
            result = engine.index_repository(
                "test-owner/test-repo",
                force_refresh=force_refresh,
                force_redownload=force_redownload,
                force_rechunk=force_rechunk,
                force_reembed=force_reembed
            )
            
            # Verify the repository info was fetched
            mock_github_fetcher.get_repository_info.assert_called_once_with("test-owner/test-repo")
            
            # Verify repository was checked in the database
            mock_chroma_db.get_repository.assert_called_once_with("test-owner/test-repo")
            
            # Verify repository contents were fetched
            assert mock_github_fetcher.fetch_repository_contents.call_count > 0
            
            # Verify chunks were processed and stored
            assert mock_chunker.chunk_repository.call_count > 0
            mock_chroma_db.store_chunks.assert_called_once_with(sample_chunks)
            
            # Verify repository info was updated in the database
            assert mock_chroma_db.add_repository.call_count > 0
            
            # Verify temp directory was cleaned up
            assert mock_rmtree.call_count > 0
            
            # Verify the returned repository info is correct
            assert result.owner == "test-owner"
            assert result.name == "test-repo"
            assert result.commit_hash == "abcd1234"
