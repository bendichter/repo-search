"""Search engine for RepoSearch."""

import datetime
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from repo_search.config import config
from repo_search.database.base import VectorDatabase
from repo_search.database.chroma import ChromaVectorDatabase
from repo_search.embedding.openai import OpenAIEmbedder
from repo_search.github.repository import GitHubRepositoryFetcher
from repo_search.models import DocumentChunk, RepositoryInfo, SearchResult
from repo_search.processing.chunker import RepositoryChunker


class SearchEngine:
    """Search engine for GitHub repositories."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        """Initialize the search engine.

        Args:
            db_path: Path to the database directory. If None, will use the path from
                config.
            api_key: OpenAI API key. If None, will use the key from config.
            token: GitHub token for authentication. If None, will use anonymous access.
        """
        self.db_path = db_path or config.db_path
        self.api_key = api_key or config.openai_api_key
        self.token = token or config.github_token

        # Initialize components
        self.embedder = OpenAIEmbedder(api_key=self.api_key)
        self.db = ChromaVectorDatabase(db_path=self.db_path, embedder=self.embedder)
        self.repo_fetcher = GitHubRepositoryFetcher(token=self.token)
        self.chunker = RepositoryChunker()

    def index_repository(
        self, 
        repository: str, 
        force_refresh: bool = False,
        force_redownload: bool = False,
        force_rechunk: bool = False,
        force_reembed: bool = False
    ) -> RepositoryInfo:
        """Index a GitHub repository.

        Args:
            repository: Repository name in the format 'owner/name'.
            force_refresh: If True, forces re-indexing of all steps even if commit hash is unchanged.
            force_redownload: If True, forces re-downloading the repository.
            force_rechunk: If True, forces re-chunking of the repository.
            force_reembed: If True, forces re-embedding of the repository chunks.

        Returns:
            Repository information.
        """
        # For backwards compatibility, force_refresh overrides the other force flags
        if force_refresh:
            force_redownload = force_rechunk = force_reembed = True
        # First, get current repository info (with the latest commit hash)
        print(f"Checking repository {repository}...")
        try:
            # This will fetch the latest repo info with commit hash
            current_repo_info = self.repo_fetcher.get_repository_info(repository)
        except Exception as e:
            print(f"Error getting repository info: {e}")
            raise

        # Check if the repository is already indexed
        existing_repo = self.db.get_repository(repository)
        
        # Initialize repo_info with current info
        repo_info = current_repo_info
        repo_dir = None
        temp_dir = None
        need_download = True
        need_chunking = True
        need_embedding = True
        # Track which files need processing at each stage
        files_to_chunk = set()
        files_to_delete = set()
        
        # If already indexed, check what steps we can skip
        if existing_repo:
            # Check if commit hash is the same (no change in repository content)
            if existing_repo.commit_hash and existing_repo.commit_hash == current_repo_info.commit_hash and not force_refresh:
                # Apply force parameters to override need_* flags
                if force_redownload:
                    print(f"Forcing re-download of repository {repository}...")
                    need_download = True
                elif existing_repo.download_successful:
                    print(f"Repository {repository} is already downloaded successfully, skipping download.")
                    need_download = False
                else:
                    print(f"Previous download was unsuccessful, re-downloading repository.")
                
                # Chunking and embedding can be skipped only if download is skipped
                if not need_download:
                    if force_rechunk:
                        print(f"Forcing re-chunking of repository {repository}...")
                        need_chunking = True
                    elif existing_repo.chunking_successful:
                        print(f"Repository {repository} was previously chunked successfully, skipping chunking.")
                        need_chunking = False
                    else:
                        print(f"Previous chunking was unsuccessful, re-chunking repository.")
                
                    if not need_chunking:
                        if force_reembed:
                            print(f"Forcing re-embedding of repository {repository}...")
                            need_embedding = True
                        elif existing_repo.embedding_successful:
                            print(f"Repository {repository} was previously embedded successfully, skipping embedding.")
                            need_embedding = False
                        else:
                            print(f"Previous embedding was unsuccessful, re-embedding repository.")
                
                # If we're skipping everything, return the existing repo info
                if not need_download and not need_chunking and not need_embedding:
                    print(f"Repository {repository} is already fully indexed with the same commit hash.")
                    print(f"Latest commit: {existing_repo.commit_hash}")
                    print(f"Last indexed: {existing_repo.last_indexed}")
                    print(f"Number of chunks: {existing_repo.num_chunks}")
                    return existing_repo
            else:
                # Repository has changed or force refresh
                if force_refresh:
                    print(f"Forcing refresh of repository {repository}...")
                else:
                    print(f"Repository {repository} has changed (commit {current_repo_info.commit_hash}).")
                    print(f"Previous commit: {existing_repo.commit_hash or 'unknown'}")
                
                # Copy over file hashes from existing repo for comparison later
                if hasattr(existing_repo, 'file_hashes') and existing_repo.file_hashes:
                    repo_info.file_hashes = existing_repo.file_hashes.copy()
                
                # Copy over non-commit-related metadata from existing repo
                repo_info.num_chunks = existing_repo.num_chunks
                repo_info.num_files = existing_repo.num_files
        else:
            print(f"Repository {repository} is not yet indexed.")
        
        # Step 1: Download repository if needed
        if need_download:
            # Create a temporary directory for the repository contents
            temp_dir = tempfile.mkdtemp(prefix=f"reposearch_")
            try:
                # Fetch the repository contents
                print(f"Fetching repository {repository}...")
                downloaded_repo_info, repo_dir = self.repo_fetcher.fetch_repository_contents(
                    repository, Path(temp_dir)
                )
                
                # If we have existing file hashes, compare to identify changed files
                if existing_repo and hasattr(existing_repo, 'file_hashes') and existing_repo.file_hashes:
                    # Get new file hashes from the downloaded repo
                    new_file_hashes = downloaded_repo_info.file_hashes
                    old_file_hashes = existing_repo.file_hashes
                    
                    # Find files that are new or modified
                    for file_path, file_hash in new_file_hashes.items():
                        if file_path not in old_file_hashes or old_file_hashes[file_path] != file_hash:
                            # File is new or modified, needs processing
                            files_to_chunk.add(file_path)
                            print(f"File changed or added: {file_path}")
                    
                    # Find files that were deleted
                    for file_path in old_file_hashes:
                        if file_path not in new_file_hashes:
                            files_to_delete.add(file_path)
                            print(f"File deleted: {file_path}")
                    
                    # If we have specific files to process, we need partial chunking
                    if files_to_chunk and not force_rechunk:
                        print(f"Detected {len(files_to_chunk)} changed files and {len(files_to_delete)} deleted files")
                        need_chunking = True  # We need to chunk, but only specific files
                else:
                    # No previous file hashes or forced rechunk - process all files
                    print("No previous file hashes available, will process all files")
                    need_chunking = True
                    if repo_dir:
                        # Get list of all files in the repository
                        for file_path in self.repo_fetcher.get_text_files(repo_dir):
                            rel_path = file_path.relative_to(repo_dir)
                            files_to_chunk.add(str(rel_path))
                
                # Update repo_info with download results
                repo_info.num_files = downloaded_repo_info.num_files
                repo_info.download_successful = True
                
                # Update file hashes with the latest from GitHub
                repo_info.file_hashes = downloaded_repo_info.file_hashes
                
                # Store repository info (partial update)
                self.db.add_repository(repo_info)
            except Exception as e:
                print(f"Error downloading repository: {e}")
                repo_info.download_successful = False
                self.db.add_repository(repo_info)
                raise
        
        # Step 2: Chunk repository if needed
        chunks = []
        if need_chunking and repo_dir:
            # If we have specific files to chunk
            if files_to_chunk and not force_rechunk:
                print(f"Chunking {len(files_to_chunk)} changed/new files...")
                try:
                    # Delete chunks for deleted files
                    if files_to_delete:
                        print(f"Removing chunks for {len(files_to_delete)} deleted files...")
                        for file_path in files_to_delete:
                            self.db.delete_file_chunks(repository, file_path)
                    
                    # Chunk only the changed files
                    for file_path in files_to_chunk:
                        file_full_path = repo_dir / file_path
                        # Check if file exists (might have been deleted)
                        if file_full_path.exists() and file_full_path.is_file():
                            # Remove existing chunks for this file
                            self.db.delete_file_chunks(repository, file_path)
                            
                            # Check if it's a text file
                            if self.repo_fetcher.is_text_file(file_full_path):
                                # Chunk the file
                                print(f"Chunking file: {file_path}")
                                file_chunks = self.chunker.text_chunker.chunk_file(file_full_path, repository)
                                chunks.extend(file_chunks)
                    
                    print(f"Generated {len(chunks)} chunks from changed files.")
                    repo_info.chunking_successful = True
                    self.db.add_repository(repo_info)
                except Exception as e:
                    print(f"Error chunking changed files: {e}")
                    repo_info.chunking_successful = False
                    self.db.add_repository(repo_info)
                    if not isinstance(e, UnicodeDecodeError):  # UnicodeDecodeError is expected for some files
                        raise
            else:
                # Process all files
                print(f"Chunking all repository contents...")
                try:
                    # Delete all existing chunks
                    if existing_repo:
                        self.db.delete_repository_chunks(repository)
                    
                    # Chunk all files
                    for chunk in self.chunker.chunk_repository(repository, repo_dir):
                        chunks.append(chunk)
                    print(f"Generated {len(chunks)} chunks.")
                    repo_info.chunking_successful = True
                    self.db.add_repository(repo_info)
                except Exception as e:
                    print(f"Error chunking repository: {e}")
                    repo_info.chunking_successful = False
                    self.db.add_repository(repo_info)
                    if not isinstance(e, UnicodeDecodeError):  # UnicodeDecodeError is expected for some files
                        raise
        
        # Step 3: Embed and store chunks if needed
        if need_embedding and (chunks or not need_chunking):
            print(f"Embedding and storing chunks...")
            try:
                if chunks:
                    self.db.store_chunks(chunks)
                    # Update repository info
                    repo_info.num_chunks = len(chunks)
                repo_info.embedding_successful = True
                repo_info.last_indexed = datetime.datetime.now()
                self.db.add_repository(repo_info)
            except Exception as e:
                print(f"Error embedding repository: {e}")
                repo_info.embedding_successful = False
                self.db.add_repository(repo_info)
                raise
        
        # Cleanup
        if temp_dir:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}")
        
        return repo_info

    def search(
        self,
        query: str,
        repository: Optional[str] = None,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """Search for documents similar to a query.

        Args:
            query: Query text.
            repository: Optional repository to search in (owner/name).
            limit: Maximum number of results to return.
            score_threshold: Minimum similarity score for results.

        Returns:
            List of search results.
        """
        limit = limit or config.max_results
        score_threshold = score_threshold or config.score_threshold
        return self.db.search(query, repository, limit, score_threshold)

    def get_repository(self, repository: str) -> Optional[RepositoryInfo]:
        """Get repository information.

        Args:
            repository: Repository name in the format 'owner/name'.

        Returns:
            Repository information, or None if not found.
        """
        return self.db.get_repository(repository)

    def get_repositories(self) -> List[RepositoryInfo]:
        """Get all indexed repositories.

        Returns:
            List of repository information.
        """
        return self.db.list_repositories()

    def delete_repository(self, repository: str) -> bool:
        """Delete a repository from the index.

        Args:
            repository: Repository name in the format 'owner/name'.

        Returns:
            True if the repository was deleted, False if it was not found.
        """
        return self.db.delete_repository(repository)

    def clear(self) -> None:
        """Clear all data from the index."""
        self.db.clear()
