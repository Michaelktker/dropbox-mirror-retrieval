# Phase 7 Testing Guide

## Current Status: BLOCKED ⚠️

**Issue**: Dropbox app token has `account_info.read` scope only — missing file access permissions.

**Last execution**: `sync-dropbox-to-gcs` failed with `AuthError('invalid_access_token')`

---

## Quick Start: Unblock & Test

### Option 1: Run Diagnostic (Check Current Status)

```bash
bash infra/check_dropbox_permissions.sh
```

This will test your current token and tell you exactly what's wrong.

### Option 2: Fix Permissions & Resume Testing

#### Step 1: Fix Dropbox App Permissions

1. **Open**: https://www.dropbox.com/developers/apps/info/oyvml1upnprceii
2. **Click**: "Permissions" tab
3. **Enable** these permissions:
   - ✅ `files.metadata.read`
   - ✅ `files.content.read`
4. **Click**: "Submit" button at bottom

#### Step 2: Re-authorize & Update Token

```bash
# This script will:
# 1. Give you an auth URL
# 2. Exchange the code for a refresh token
# 3. Update Secret Manager automatically
bash infra/reauthorize_dropbox.sh
```

#### Step 3: Run All Tests

```bash
# Comprehensive test suite (Tests A, C, D, E, F, G)
bash infra/run_all_tests.sh
```

**Or run tests individually:**

```bash
# Test A: Baseline sync
bash infra/test_sync.sh

# Test C: Image embeddings
bash infra/test_embeddings.sh

# Test D: Document search
bash infra/test_doc_search.sh

# Test E: Image vector search
bash curl/query_vector_search.sh "photo of mountains"

# Test F: Combined retrieval
bash curl/combine_results.sh "meeting presentation"

# Test G: Scheduler trigger
gcloud scheduler jobs run daily-dropbox-sync --location=us-central1
```

---

## Test Coverage

### Automated Tests

- ✅ **Test A**: Baseline sync (full Dropbox → GCS)
- ✅ **Test C**: Image embeddings (multimodal → Vector Search)
- ✅ **Test D**: Document search (Vertex AI Search import)
- ✅ **Test E**: Image search (vector similarity query)
- ✅ **Test F**: Combined retrieval (images + documents)
- ✅ **Test G**: Scheduler trigger

### Manual Tests

- **Test B**: Incremental sync
  1. Modify files in Dropbox (add/delete/rename)
  2. Re-run: `bash infra/test_sync.sh`
  3. Verify GCS reflects changes

---

## Troubleshooting

### Job logs

```bash
# Sync job logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=sync-dropbox-to-gcs" \
  --limit=50 --format=json

# Embed job logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=embed-images-to-vector-search" \
  --limit=50 --format=json
```

### Check bucket content

```bash
source infra/variables.sh

# List all files
gsutil ls -r "gs://${BUCKET_NAME}/mirror/"

# Check state files
gsutil cat "gs://${BUCKET_NAME}/mirror/state/sync_state.json"
gsutil cat "gs://${BUCKET_NAME}/mirror/state/path_index.json"
gsutil cat "gs://${BUCKET_NAME}/mirror/state/embedding_state.json"
```

### Check Vector Search index

```bash
export VECTOR_SEARCH_INDEX_ID=8915836435542573056
gcloud ai indexes describe $VECTOR_SEARCH_INDEX_ID --region=us-central1
```

### Check Vertex AI Search

```bash
gcloud alpha discovery-engine datastores describe dropbox-docs-datastore \
  --location=global --project=gen-lang-client-0540480379
```

---

## Success Criteria

After all tests pass:

1. ✅ GCS bucket has files in `mirror/images/`, `mirror/docs/`, `mirror/media/`
2. ✅ Metadata files exist in `mirror/meta/`
3. ✅ State files track sync cursor, paths, embeddings
4. ✅ Vector Search returns image results
5. ✅ Vertex AI Search returns document results
6. ✅ Combined queries work
7. ✅ Schedulers trigger jobs successfully

**Then**: Update IMPLEMENTATION_PLAN.md and mark Phase 7 & 8 complete! 🎉
