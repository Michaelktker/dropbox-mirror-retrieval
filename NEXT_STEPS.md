# 🚀 READY TO TEST — Next Steps

## Current Situation

✅ **Infrastructure**: Complete (GCS, Vector Search, Vertex AI Search, Cloud Run Jobs, Schedulers)  
⚠️ **Blocker**: Dropbox app permissions — token has `account_info.read` only

## Immediate Action Required

### Step 1: Check Current Status (30 seconds)

```bash
cd /workspaces/dropbox-mirror-retrieval
bash infra/check_dropbox_permissions.sh
```

This will test your Dropbox token and tell you exactly what needs to be fixed.

---

### Step 2: Fix Dropbox Permissions (2 minutes)

1. **Open** your browser: https://www.dropbox.com/developers/apps/info/oyvml1upnprceii
2. **Click** the "Permissions" tab
3. **Enable** these checkboxes:
   - ✅ `files.metadata.read`
   - ✅ `files.content.read`
4. **Click** "Submit" at the bottom

---

### Step 3: Re-authorize (1 minute)

```bash
bash infra/reauthorize_dropbox.sh
```

This script will:
- Give you an authorization URL
- Exchange your auth code for a new refresh token
- Update the GCP secret automatically

---

### Step 4: Run All Tests (10-15 minutes)

```bash
bash infra/run_all_tests.sh
```

This comprehensive test suite will:
- ✅ Test A: Baseline sync (Dropbox → GCS)
- ✅ Test C: Image embeddings (→ Vector Search)
- ✅ Test D: Document search (→ Vertex AI Search)
- ✅ Test E: Image vector search query
- ✅ Test F: Combined retrieval query
- ✅ Test G: Scheduler trigger

---

## Alternative: Run Tests Individually

```bash
# Test sync (Test A)
bash infra/test_sync.sh

# Test embeddings (Test C)
bash infra/test_embeddings.sh

# Test document search (Test D)
bash infra/test_doc_search.sh

# Test image search (Test E)
bash curl/query_vector_search.sh "photo of mountains"

# Test combined (Test F)
bash curl/combine_results.sh "meeting presentation"

# Test scheduler (Test G)
gcloud scheduler jobs run daily-dropbox-sync --location=us-central1
```

---

## Manual Test: Incremental Sync (Test B)

After baseline sync works:

1. **Modify Dropbox**: Add/delete/rename files
2. **Re-run sync**: `bash infra/test_sync.sh`
3. **Verify**: Check that GCS reflects changes

---

## What Happens When All Tests Pass?

1. ✅ GCS bucket has your Dropbox files organized by category
2. ✅ Images are embedded in Vector Search (searchable by text)
3. ✅ Documents are indexed in Vertex AI Search
4. ✅ Combined queries return both images and documents
5. ✅ Schedulers will run daily at 02:00, 04:00, 05:00 UTC
6. ✅ System is **production-ready**!

Then:
- Update [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) checkboxes
- Commit and push to GitHub
- **Project complete!** 🎉

---

## Need Help?

**Detailed guides:**
- [TESTING.md](TESTING.md) — Comprehensive testing documentation
- [README.md](README.md) — Full architecture and setup guide
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — Phase-by-phase checklist

**Check logs:**
```bash
# Sync job logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=sync-dropbox-to-gcs" \
  --limit=50

# Embed job logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=embed-images-to-vector-search" \
  --limit=50
```

**Check GCS bucket:**
```bash
source infra/variables.sh
gsutil ls -r "gs://${BUCKET_NAME}/mirror/"
```

---

## Time Estimate

| Task | Time |
|------|------|
| Check permissions | 30 seconds |
| Fix Dropbox app settings | 2 minutes |
| Re-authorize | 1 minute |
| Run all tests | 10-15 minutes |
| **Total** | **~15 minutes** |

**You're 15 minutes away from a working system!** 🚀
