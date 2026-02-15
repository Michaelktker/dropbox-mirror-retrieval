import os
content = """# Skill: Dropbox Mirror Search

Search images and documents from a Dropbox mirror stored in Google Cloud.

## Prerequisites

- gcloud CLI installed and authenticated
- Python 3 installed
- Access to GCP project gen-lang-client-0540480379

## Environment Setup

```bash
export GCP_PROJECT_ID="gen-lang-client-0540480379"
export GCP_REGION="us-central1"
export VECTOR_SEARCH_ENDPOINT_ID="2432588112593944576"
export VECTOR_SEARCH_DEPLOYED_INDEX_ID="deployed_dropbox_images"
export VERTEX_SEARCH_DATASTORE_ID="dropbox-docs-datastore-ocr"
```

## Capabilities

### 1. Search Images

```bash
bash curl/query_vector_search.sh "sunset over the ocean"
```

### 2. Search Documents

```bash
bash curl/query_vertex_search.sh "meeting notes"
```

### 3. Combined Search

```bash
bash curl/combine_results.sh "presentation"
```

## Resource Details

- GCP Project: gen-lang-client-0540480379- GCP Project: gen-lang-client-0540480379- GCP Project: gen-lang-client-0540480379- GCP Project: gen-lang-client-0540480oint: 2432588112593944576
- Vertex Search Datastore: drop- Vertex Search Datastore: drop- Vertex Search Datastore: drop- Vertexindex- Vertex Searceddi- Vertex Search Datastore: drop- 
- Sync - Sync - Sync - Syn 0- Sync - Sync - Sync - Syn 0- Sync - Sync - Syn   f.- Sync - Sync - Synt("- Syncmd created")
os.remove("create_skill.py")
