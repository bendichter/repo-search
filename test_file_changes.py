#!/usr/bin/env python
"""Test script for file-level change detection."""

import sys
from repo_search.api.client import RepoSearchClient

def main():
    """Main function."""
    # Initialize the client
    client = RepoSearchClient()
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_file_changes.py <repository>")
        print("Example: python test_file_changes.py owner/repo")
        return
    
    repository = sys.argv[1]
    
    # Index the repository with file-level change detection
    print(f"Indexing repository: {repository}")
    print("First run will download, chunk, and embed all files.")
    repo_info = client.index_repository(repository)
    
    print("\n" + "="*80)
    print(f"Repository '{repository}' indexed successfully.")
    print(f"Commit hash: {repo_info.commit_hash}")
    print(f"Number of files: {repo_info.num_files}")
    print(f"Number of chunks: {repo_info.num_chunks}")
    print(f"File hashes stored: {len(repo_info.file_hashes)}")
    print("="*80 + "\n")
    
    print("Run again to see file-level change detection in action.")
    print("Only modified files will be re-processed on subsequent runs.")
    print("You can try:")
    print(f"  python test_file_changes.py {repository}")
    
if __name__ == "__main__":
    main()
