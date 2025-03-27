# RepoSearch

RepoSearch is a tool for semantic search over GitHub repositories. It chunks repository content, generates semantic embeddings, and stores them in a vector database for efficient semantic search.

## Features

- Clone GitHub repositories by owner/name format
- Process all text files in the repository
- Chunk content using intelligent chunking strategies
- Generate semantic embeddings using OpenAI
- Store embeddings in a vector database with a flexible backend
- Provide semantic search capabilities through a Python API
- **Smart file-level change detection** - Only re-process files that have changed since the last indexing, improving performance for large repositories

## Optimized Indexing

RepoSearch uses GitHub's file SHA hashes to detect which files have changed between indexing operations:

- First run: Downloads, chunks, and embeds all repository files
- Subsequent runs: Only re-processes files that have been added, modified, or deleted
- Automatic cleanup: Removes chunks for deleted files from the vector database
- Preserves repository structure: Maintains all metadata while optimizing processing time

## Getting Started

### Prerequisites

- Python 3.9 or higher
- OpenAI API key 

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/repo-search.git
cd repo-search

# Install the package
pip install -e .
```

### Configuration

Create a `.env` file in the root directory with the following content:

```
OPENAI_API_KEY=your_openai_api_key
```

You can also optionally configure:
```
GITHUB_TOKEN=your_github_token
DATA_DIR=data
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BATCH_SIZE=16
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
MAX_RESULTS=10
SCORE_THRESHOLD=0.0
```

### Usage

```python
from repo_search.api.client import RepoSearchClient

# Initialize the client
client = RepoSearchClient()

# Index a repository - automatically uses file-level change detection
client.index_repository("owner/repo")

# Force options are available if needed
# client.index_repository("owner/repo", force_redownload=True)  # Force re-download
# client.index_repository("owner/repo", force_rechunk=True)     # Force re-chunking
# client.index_repository("owner/repo", force_reembed=True)     # Force re-embedding
# client.index_repository("owner/repo", force_refresh=True)     # Force complete refresh

# Perform a semantic search
results = client.semantic_search("How to implement authentication?")

# Print results
for result in results:
    print(f"Score: {result.score}")
    print(f"Content: {result.content}")
    print(f"Source: {result.source}")
    print("---")
```

### Add to Cline

```json
{
  "mcpServers": {
    "repo-search": {
      "command": "python",
      "args": [
        "/path/to/repo-search/src/mcp/server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
