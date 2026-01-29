# [Alternative & Metal Releases](https://mushroomoff.github.io)
There will be some description... soon!

## Index
### Root folder
- *index.html* - main HTML with upcoming releases
- *README.md* - read me
- *status.log* - GitHub Actions log

### /.github/workflows
- *AMR_LookApp.yml* - YAML to run GitHub Action "AMR LookApp" on schedule: Every Friday at 3:39 UTC (+/- 15 min). 3:39 UTC is 6:39 in Moscow
- *AMR_NewReleases.yml* - YAML to run GitHub Action "AMR New Releases" on schedule: Every Friday at 5:09 UTC (+/- 15 min). 5:09 UTC is 8:09 in Moscow.

### /AMRs
- *AMR YYYY-MM.html* - HTMLs for each month with new releases (YYYY - year, MM - month)

> ### /Covers (ignored from GitHub)
> - */New Covers* - folder to download new covers
> - */Fresh Covers to Check* - folder that stores new covers to check manualy

### /Databases
- *AMR_artisitGenres.txt* - list of Artists with Genres for MP3 tags
- *AMR_artisitIDs.csv* - CSV of Artists Apple Music IDs for LookApp
- *AMR_csReleases_DB.csv* - CSV of Coming Soon releases (shown on main HTML)
- *AMR_newReleases_DB.csv* - CSV of New releases (shown on AMR HTMLs)
- *AMR_releases_DB.csv* - CSV of all releases for Artists in "AMR_artisitIDs.csv"

### /Python Notebooks
- *AMR Check Database v.2.024.ipynb* - PyNotebook to work with all releases database "AMR_releases_DB.csv". Here all releases must be marked for downloading (empty - to download, 'v' - downloaded, 'x' - no need to download). Here stores the script for "AMR_List2Download_local.py"
- *AMR Covers Downloader v.2.024.ipynb* - PyNotebook contains script for "AMR_CoversDownloader_local.py"
- *AMR LookApp v.2.024.ipynb* - PyNotebook contains script for "AMR_LookApp_local.py" and "AMR_LookApp_github.py"
- *AMR New Releases v.2.024.ipynb* - PyNotebook contains script for "AMR_NewReleases_local.py" and "AMR_NewReleases_github.py"
- *requirements.txt* - third party packages for Python (used to run GitHub Actions)

### /Python Scripts
- *AMR_CoversDownloader_local.py* - There will be some description... soon!
- *AMR_List2Download_local.py* - There will be some description... soon!
- *AMR_LookApp_github.py* - There will be some description... soon!
- *AMR_LookApp_local.py* - There will be some description... soon!
- *AMR_NewReleases_github.py* - There will be some description... soon!
- *AMR_NewReleases_local.py* - There will be some description... soon!

### \resources
- *favicon-2.ico* - site favourite icon
- *favicon.ico* - site favourite icon
- *index.css* - CSS #1
- *styles.css* - CSS #2
- *touch-icon-\** - mobile devices favourite icon

2022-2024 by Viktor 'MushroomOFF' Gribov
