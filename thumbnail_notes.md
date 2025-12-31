# Representative Image Fetching Notes

Research on how to fetch representative thumbnail images for each study from IDR, SSBD, and BIA.

## IDR (via OMERO API)

IDR uses OMERO for image management. The API hierarchy is:
- Projects/Screens → Datasets/Plates → Images

### API Endpoints

```bash
# List all projects
curl "https://idr.openmicroscopy.org/api/v0/m/projects/"

# List all screens (for HCS data)
curl "https://idr.openmicroscopy.org/api/v0/m/screens/"

# Get datasets in a project
curl "https://idr.openmicroscopy.org/api/v0/m/projects/{project_id}/datasets/"

# Get images in a dataset
curl "https://idr.openmicroscopy.org/api/v0/m/datasets/{dataset_id}/images/?limit=1"
```

### Thumbnail Endpoint

```bash
# Get thumbnail (JPEG) - size in pixels
curl "https://idr.openmicroscopy.org/webgateway/render_birds_eye_view/{image_id}/256/" -o thumb.jpg
```

### Example

```bash
# Project 101 → Dataset 369 → Image 1920093
curl "https://idr.openmicroscopy.org/webgateway/render_birds_eye_view/1920093/256/" -o idr_thumb.jpg
# Result: 256x215 JPEG
```

### Mapping Study ID to Image

IDR study IDs (e.g., `idr0018`) map to project/screen names. Need to:
1. Search projects/screens by name prefix
2. Get first dataset
3. Get first image
4. Fetch thumbnail

## SSBD (via OMERO API)

SSBD also uses OMERO, same API structure as IDR.

**Note:** SSBD has SSL certificate issues - use `-k` flag with curl.

### API Endpoints

```bash
# List projects
curl -k "https://ssbd.riken.jp/omero/api/v0/m/projects/"

# Get datasets
curl -k "https://ssbd.riken.jp/omero/api/v0/m/projects/{project_id}/datasets/"

# Get images
curl -k "https://ssbd.riken.jp/omero/api/v0/m/datasets/{dataset_id}/images/?limit=1"
```

### Thumbnail Endpoint

```bash
curl -k "https://ssbd.riken.jp/omero/webgateway/render_birds_eye_view/{image_id}/256/" -o thumb.jpg
```

### Example

```bash
# Project 302 → Dataset 1908 → Image 119801
curl -k "https://ssbd.riken.jp/omero/webgateway/render_birds_eye_view/119801/256/" -o ssbd_thumb.jpg
# Result: 256x210 JPEG
```

### Mapping Study ID to Image

SSBD project names like `100-Yamamoto-ToothDev` contain the numeric ID. Need to:
1. List projects and match by ID prefix
2. Get first dataset
3. Get first image
4. Fetch thumbnail

## BIA (S3-based)

BIA provides thumbnail URLs directly in the search API response.

### From Search API

The search response includes `example_image_uri` at the dataset level:

```json
{
  "dataset": [{
    "example_image_uri": [
      "https://uk1s3.embassy.ebi.ac.uk/bia-integrator-data/S-BIAD2455/dd659dc5-1b82-4290-920d-b7a89e3c7217/static_display_512_512.png"
    ],
    "image": [{
      "additional_metadata": [{
        "name": "image_thumbnail_uri",
        "value": {
          "256": {
            "uri": "https://uk1s3.embassy.ebi.ac.uk/bia-integrator-data/S-BIAD2455/477bcc36-8630-4eb6-9c96-679eef90a04f/thumbnail_256_256.png",
            "size": 256
          }
        }
      }]
    }]
  }]
}
```

### Thumbnail URLs

```bash
# Representative image (512x512)
curl "https://uk1s3.embassy.ebi.ac.uk/bia-integrator-data/{accession}/{uuid}/static_display_512_512.png"

# Thumbnail (256x256)
curl "https://uk1s3.embassy.ebi.ac.uk/bia-integrator-data/{accession}/{uuid}/thumbnail_256_256.png"
```

### Example

```bash
curl "https://uk1s3.embassy.ebi.ac.uk/bia-integrator-data/S-BIAD2455/dd659dc5-1b82-4290-920d-b7a89e3c7217/thumbnail_256_256.png" -o bia_thumb.png
# Result: 256x256 PNG
```

### Mapping Study ID to Image

BIA is simplest - the search API already returns `example_image_uri`. Just need to:
1. Extract `dataset[0].example_image_uri[0]` from search response
2. Fetch directly (no authentication needed)

## Summary

| Source | Format | Size | Auth Required | Complexity |
|--------|--------|------|---------------|------------|
| IDR | JPEG | 256xN | No | High (3 API calls to find image ID) |
| SSBD | JPEG | 256xN | No (SSL issues) | High (3 API calls to find image ID) |
| BIA | PNG | 256x256 or 512x512 | No | Low (URL in search response) |

## Implementation Notes

### For BIA
- Modify `BIATransformer` to extract and store `example_image_uri` during transformation
- Add `thumbnail_url` field to Study schema

### For IDR/SSBD
- Need to build OMERO ID mappings during transformation
- Store project/dataset/image IDs in study metadata
- Or: build a separate thumbnail resolution service

### Alternative Approach
- Create a `/thumbnail/{study_id}` API endpoint that resolves and proxies thumbnails
- Cache thumbnails locally to avoid repeated API calls
- Handle SSBD SSL issues server-side
