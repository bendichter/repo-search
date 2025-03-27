"""Tests for the GitHub repository module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock, call

import pytest
from github.ContentFile import ContentFile
from github.Repository import Repository

from repo_search.github.repository import GitHubRepositoryFetcher
from repo_search.models import RepositoryInfo


class TestGitHubRepositoryFetcher:
    """Test the GitHubRepositoryFetcher class."""

    def test_initialization_no_token(self):
        """Test initialization without a token."""
        with patch('repo_search.github.repository.Github') as mock_github, \
             patch('repo_search.github.repository.config') as mock_config:
            # Set config token to None to simulate no token
            mock_config.github_token = None
            
            fetcher = GitHubRepositoryFetcher()
            mock_github.assert_called_once_with()
            assert fetcher.token is None
            assert fetcher.github == mock_github.return_value

    def test_initialization_with_token(self):
        """Test initialization with a token."""
        with patch('repo_search.github.repository.Github') as mock_github:
            fetcher = GitHubRepositoryFetcher(token="test-token")
            mock_github.assert_called_once_with("test-token")
            assert fetcher.token == "test-token"
            assert fetcher.github == mock_github.return_value

    def test_get_repository_info(self):
        """Test getting repository information."""
        with patch('repo_search.github.repository.Github') as mock_github:
            # Setup mock repository
            mock_repo = MagicMock(spec=Repository)
            mock_repo.html_url = "https://github.com/test-owner/test-repo"
            
            # Setup mock commit
            mock_commit = MagicMock()
            mock_commit.sha = "abcd1234"
            
            # Set up mock repository to return our mock commit
            mock_repo.get_commits.return_value = [mock_commit]
            
            # Set up GitHub client to return our mock repository
            mock_github_instance = mock_github.return_value
            mock_github_instance.get_repo.return_value = mock_repo
            
            fetcher = GitHubRepositoryFetcher()
            result = fetcher.get_repository_info("test-owner/test-repo")
            
            # Verify the repository was fetched correctly
            mock_github_instance.get_repo.assert_called_once_with("test-owner/test-repo")
            mock_repo.get_commits.assert_called_once()
            
            # Verify the returned repository info is correct
            assert isinstance(result, RepositoryInfo)
            assert result.owner == "test-owner"
            assert result.name == "test-repo"
            assert result.url == "https://github.com/test-owner/test-repo"
            assert result.commit_hash == "abcd1234"

    def test_get_repository_info_invalid_name(self):
        """Test getting repository information with an invalid repository name."""
        fetcher = GitHubRepositoryFetcher()
        
        with pytest.raises(ValueError, match="Invalid repository name"):
            fetcher.get_repository_info("invalid-repo-name")

    def test_get_repository_info_not_found(self):
        """Test getting repository information when the repository is not found."""
        with patch('repo_search.github.repository.Github') as mock_github:
            # Set up GitHub client to raise an exception
            mock_github_instance = mock_github.return_value
            mock_github_instance.get_repo.side_effect = Exception("Repository not found")
            
            fetcher = GitHubRepositoryFetcher()
            
            with pytest.raises(ValueError, match="Error accessing repository"):
                fetcher.get_repository_info("test-owner/test-repo")

    def test_fetch_repository_contents(self, temp_dir):
        """Test fetching repository contents."""
        with patch.object(GitHubRepositoryFetcher, 'get_repository_info') as mock_get_info, \
             patch.object(GitHubRepositoryFetcher, '_download_repository') as mock_download:
            
            # Setup mock repository info
            mock_repo_info = RepositoryInfo(
                owner="test-owner",
                name="test-repo",
                url="https://github.com/test-owner/test-repo",
                commit_hash="abcd1234"
            )
            mock_get_info.return_value = mock_repo_info
            
            fetcher = GitHubRepositoryFetcher()
            result_info, result_dir = fetcher.fetch_repository_contents("test-owner/test-repo", temp_dir)
            
            # Verify the repository info was fetched correctly
            mock_get_info.assert_called_once_with("test-owner/test-repo")
            
            # Verify the repository was downloaded correctly
            mock_download.assert_called_once_with(mock_repo_info, temp_dir)
            
            # Verify the returned values
            assert result_info == mock_repo_info
            assert result_dir == temp_dir

    def test_fetch_repository_contents_temp_dir(self):
        """Test fetching repository contents with a temporary directory."""
        with patch.object(GitHubRepositoryFetcher, 'get_repository_info') as mock_get_info, \
             patch.object(GitHubRepositoryFetcher, '_download_repository') as mock_download, \
             patch('tempfile.mkdtemp') as mock_mkdtemp:
            
            # Setup mock repository info
            mock_repo_info = RepositoryInfo(
                owner="test-owner",
                name="test-repo",
                url="https://github.com/test-owner/test-repo",
                commit_hash="abcd1234"
            )
            mock_get_info.return_value = mock_repo_info
            
            # Setup mock temp directory
            mock_temp_dir = "/tmp/test-owner_test-repo_123456"
            mock_mkdtemp.return_value = mock_temp_dir
            
            fetcher = GitHubRepositoryFetcher()
            result_info, result_dir = fetcher.fetch_repository_contents("test-owner/test-repo")
            
            # Verify the repository info was fetched correctly
            mock_get_info.assert_called_once_with("test-owner/test-repo")
            
            # Verify the temporary directory was created correctly
            mock_mkdtemp.assert_called_once_with(prefix="test-owner_test-repo_")
            
            # Verify the repository was downloaded correctly
            mock_download.assert_called_once_with(mock_repo_info, Path(mock_temp_dir))
            
            # Verify the returned values
            assert result_info == mock_repo_info
            assert result_dir == Path(mock_temp_dir)

    def test_is_text_file_true(self, temp_dir):
        """Test checking if a file is a text file - positive case."""
        # Create a test text file
        test_file = temp_dir / "test.txt"
        test_file.write_text("This is a test text file.")
        
        fetcher = GitHubRepositoryFetcher()
        result = fetcher.is_text_file(test_file)
        
        assert result is True

    def test_is_text_file_false_binary(self, temp_dir):
        """Test checking if a file is a text file - negative case for binary files."""
        # Create a test binary file
        test_file = temp_dir / "test.bin"
        test_file.write_bytes(b'\x00\x01\x02\x03\x04\x05')
        
        fetcher = GitHubRepositoryFetcher()
        result = fetcher.is_text_file(test_file)
        
        assert result is False

    def test_is_text_file_false_extension(self, temp_dir):
        """Test checking if a file is a text file - negative case for non-text extensions."""
        # Create a test file with a non-text extension but with text content
        test_file = temp_dir / "test.exe"
        test_file.write_text("This is actually text content but with a .exe extension")
        
        fetcher = GitHubRepositoryFetcher()
        result = fetcher.is_text_file(test_file)
        
        assert result is False

    def test_get_text_files(self, temp_dir):
        """Test getting all text files in a directory."""
        # Create some test files
        (temp_dir / "test.txt").write_text("Text file 1")
        (temp_dir / "test.md").write_text("Text file 2")
        (temp_dir / "test.py").write_text("def test(): return True")
        (temp_dir / "test.bin").write_bytes(b'\x00\x01\x02\x03')
        
        # Create a subdirectory with some more files
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test2.txt").write_text("Text file in subdir")
        (subdir / "test2.bin").write_bytes(b'\x04\x05\x06\x07')
        
        with patch.object(GitHubRepositoryFetcher, 'is_text_file') as mock_is_text:
            # Configure the mock to return True for text files
            def is_text_side_effect(path):
                return path.suffix in ['.txt', '.md', '.py']
            
            mock_is_text.side_effect = is_text_side_effect
            
            fetcher = GitHubRepositoryFetcher()
            result = list(fetcher.get_text_files(temp_dir))
            
            # We should have 4 text files in total
            assert len(result) == 4
            
            # Verify all files are Path objects
            assert all(isinstance(file, Path) for file in result)
            
            # Verify all returned paths are text files
            paths = [file.relative_to(temp_dir) for file in result]
            assert Path("test.txt") in paths
            assert Path("test.md") in paths
            assert Path("test.py") in paths
            assert Path("subdir/test2.txt") in paths
