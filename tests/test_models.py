"""Tests for models.py module."""

import pytest
from datetime import datetime

from repo_search.models import RepositoryInfo, DocumentChunk, SearchResult


class TestRepositoryInfo:
    """Test the RepositoryInfo model."""

    def test_creation(self):
        """Test creating a RepositoryInfo object."""
        repo_info = RepositoryInfo(
            owner="test-owner",
            name="test-repo",
            url="https://github.com/test-owner/test-repo"
        )
        
        assert repo_info.owner == "test-owner"
        assert repo_info.name == "test-repo"
        assert repo_info.url == "https://github.com/test-owner/test-repo"
        assert repo_info.commit_hash is None
        assert repo_info.num_files == 0
        assert repo_info.num_chunks == 0
        assert repo_info.file_hashes == {}
    
    def test_full_name_property(self):
        """Test the full_name property."""
        repo_info = RepositoryInfo(
            owner="test-owner",
            name="test-repo",
            url="https://github.com/test-owner/test-repo"
        )
        
        assert repo_info.full_name == "test-owner/test-repo"
    
    def test_complete_creation(self):
        """Test creating a RepositoryInfo object with all fields."""
        last_indexed = datetime.now()
        repo_info = RepositoryInfo(
            owner="test-owner",
            name="test-repo",
            url="https://github.com/test-owner/test-repo",
            last_indexed=last_indexed,
            num_files=5,
            num_chunks=10,
            commit_hash="abcd1234",
            download_successful=True,
            chunking_successful=True,
            embedding_successful=True,
            file_hashes={
                "README.md": "hash1",
                "src/main.py": "hash2"
            }
        )
        
        assert repo_info.owner == "test-owner"
        assert repo_info.name == "test-repo"
        assert repo_info.url == "https://github.com/test-owner/test-repo"
        assert repo_info.last_indexed == last_indexed
        assert repo_info.num_files == 5
        assert repo_info.num_chunks == 10
        assert repo_info.commit_hash == "abcd1234"
        assert repo_info.download_successful is True
        assert repo_info.chunking_successful is True
        assert repo_info.embedding_successful is True
        assert repo_info.file_hashes == {"README.md": "hash1", "src/main.py": "hash2"}


class TestDocumentChunk:
    """Test the DocumentChunk model."""
    
    def test_creation(self):
        """Test creating a DocumentChunk object."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
        )
        
        assert chunk.id == "test-owner/test-repo/path/to/file.py/1"
        assert chunk.repository == "test-owner/test-repo"
        assert chunk.content == "def test_function():\n    return 'test'"
        assert chunk.metadata == {}
        assert chunk.embedding is None
    
    def test_metadata_properties(self):
        """Test the metadata properties."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
            metadata={
                "file_path": "path/to/file.py",
                "chunk_type": "code",
                "start_line": 1,
                "end_line": 2
            }
        )
        
        assert chunk.file_path == "path/to/file.py"
        assert chunk.chunk_type == "code"
        assert chunk.start_line == 1
        assert chunk.end_line == 2
    
    def test_missing_metadata_properties(self):
        """Test behavior when metadata properties are missing."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
        )
        
        assert chunk.file_path is None
        assert chunk.chunk_type == "text"  # default value
        assert chunk.start_line is None
        assert chunk.end_line is None


class TestSearchResult:
    """Test the SearchResult model."""
    
    def test_creation(self):
        """Test creating a SearchResult object."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
            metadata={
                "file_path": "path/to/file.py",
                "chunk_type": "code",
                "start_line": 1,
                "end_line": 2
            }
        )
        
        result = SearchResult(
            chunk=chunk,
            score=0.85
        )
        
        assert result.chunk == chunk
        assert result.score == 0.85
    
    def test_content_property(self):
        """Test the content property."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
        )
        
        result = SearchResult(
            chunk=chunk,
            score=0.85
        )
        
        assert result.content == "def test_function():\n    return 'test'"
    
    def test_source_property_with_line_numbers(self):
        """Test the source property with line numbers."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
            metadata={
                "file_path": "path/to/file.py",
                "start_line": 1,
                "end_line": 2
            }
        )
        
        result = SearchResult(
            chunk=chunk,
            score=0.85
        )
        
        assert result.source == "test-owner/test-repo - path/to/file.py:1-2"
    
    def test_source_property_without_line_numbers(self):
        """Test the source property without line numbers."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/path/to/file.py/1",
            repository="test-owner/test-repo",
            content="def test_function():\n    return 'test'",
            metadata={
                "file_path": "path/to/file.py",
            }
        )
        
        result = SearchResult(
            chunk=chunk,
            score=0.85
        )
        
        assert result.source == "test-owner/test-repo - path/to/file.py"
    
    def test_source_property_no_file_path(self):
        """Test the source property when no file path is available."""
        chunk = DocumentChunk(
            id="test-owner/test-repo/1",
            repository="test-owner/test-repo",
            content="Some text without a file path"
        )
        
        result = SearchResult(
            chunk=chunk,
            score=0.85
        )
        
        assert result.source == "test-owner/test-repo"
