---
name: radarr
description: Manage movies via Radarr - search, add, monitor downloads, check wanted list. Use when user asks about movies to download, checking download queue, adding films to library, or managing their Radarr instance. Triggers on mentions of Radarr, movie downloads, adding movies, download queue, wanted movies.
---

# Radarr Skill

Manage user's Radarr movie library via proxy. Large results save to disk (metadata only returned) to preserve context.

## Scripts

All at `/mnt/skills/user/radarr/scripts/`

### radarr.py

Main interface for all Radarr operations.

**Large results (movies, releases, queue, wanted) return metadata only. Full data saved to file.**

```bash
# Search for movies (returns full results - typically small)
python3 radarr.py search "The Matrix" 1999
python3 radarr.py search "Interstellar"

# List library (returns count + path only)
python3 radarr.py movies                    # All movies
python3 radarr.py movies true               # Monitored only

# Then grep the saved file to find specific movies
grep -i "hotel" /home/claude/radarr/movies_*.json

# Get movie details (returns full result)
python3 radarr.py movie 123

# Add movie by TMDB ID (get ID from search results)
python3 radarr.py add 603                   # The Matrix

# Search for releases (returns count + path only)
python3 radarr.py releases 123
# Then grep for quality/size
grep -i "1080p\|bluray" /home/claude/radarr/releases_*.json

# Download a release
python3 radarr.py download "release-guid" 123

# Check download queue (returns count + path only)
python3 radarr.py queue
grep -i "title" /home/claude/radarr/queue_*.json

# Get wanted/missing movies (returns count + path only)
python3 radarr.py wanted

# System status (returns full result)
python3 radarr.py status
```

### storage.py

Manage cached results.

```bash
python3 storage.py list              # Show all cached results
python3 storage.py get <filename>    # Load specific result
python3 storage.py clear             # Clear cache
```

## Cache Location

```
/home/claude/radarr/
├── search_*.json
├── movies_*.json
├── releases_*.json
├── queue_*.json
└── manifest.json
```

## Typical Workflows

### Check if a movie is in library
```bash
# 1. Fetch library (saves to file, returns count only)
python3 radarr.py movies
# 2. Grep the file for the movie
grep -i "hotel transylvania" /home/claude/radarr/movies_*.json
```

### Find and add a movie
```bash
# 1. Search (returns full results)
python3 radarr.py search "Dune" 2021
# 2. Note the tmdb_id from results
# 3. Add it
python3 radarr.py add 438631
```

### Check what's downloading
```bash
python3 radarr.py queue
# If items exist, grep for details
grep -i "title\|progress" /home/claude/radarr/queue_*.json
```

### Find missing movies
```bash
python3 radarr.py wanted
grep -i "title" /home/claude/radarr/wanted_*.json
```

### Manually grab a release
```bash
# 1. Get movie ID from library
python3 radarr.py movies
grep -i "movie name" /home/claude/radarr/movies_*.json | grep '"id"'
# 2. Search releases
python3 radarr.py releases 123
# 3. Find a good release
grep -i "1080p" /home/claude/radarr/releases_*.json | head -20
# 4. Download preferred release (get guid from grep output)
python3 radarr.py download "release-guid-here" 123
```

## Notes

- **Large results (movies, releases, queue, wanted) return metadata only** - full data in file
- **Small results (search, status, movie details, add) return full data**
- Grep the saved files directly, don't pipe stdout
- TMDB IDs are used for adding movies (shown in search results)
- Movie IDs (internal Radarr IDs) are used for releases/details
- Quality profiles and root folders use Radarr defaults
- Files are timestamped, use `*.json` glob to find latest
