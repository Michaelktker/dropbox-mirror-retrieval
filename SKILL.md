# Skill: Dropbox Mirror Search

Search images and documents from a Dropbox mirror stored in Google Cloud.

## Environment Setup

export GCP_PROJECT_ID=gen-lang-client-0540480379
export GCP_REGION=us-central1
export VECTOR_SEARCH_ENDPOINT_ID=2432588112593944576
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=deployed_dropbox_images
export VERTEX_SEARCH_DATASTORE_ID=dropbox-docs-datastore-ocr

## Search Images
bash curl/query_vector_search.sh "your query"

## Search Documents  
bash curl/query_vertex_search.sh "your query"

## Combined Search
bash curl/combine_results.sh "your query"

## Resources
- GCP Project: gen-lang-client-0540480379
- Vector Search Index: 3582448576829063168
- Vector Search Endpoint: 2432588112593944576
- Vertex Search Datastore: dropbox-docs-datastore-ocr

## Stats
- Images: 22252
- Documents: 4108
