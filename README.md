# [Apple Music New Releases](https://mushroomoff.github.io)
There will be some description... soon!

## Index
### Root folder
- *index.html* - main HTML with upcoming releases
- *README.md* - read me
- *status.log* - GitHub Actions log

### /.github/workflows
- *AMR_LookApp.yml* - YAML to run GitHub Action "Apple Music Releases LookApp" on schedule: Every Friday at 3:39 UTC (+/- 15 min). 3:39 UTC is 6:39 in Moscow
- *AMR_NewReleases.yml* - YAML to run GitHub Action "Apple Music New Releases" on schedule: Every Friday at 5:09 UTC (+/- 15 min). 5:09 UTC is 8:09 in Moscow.

### /AMRs
  HTMLs for each month with new releases

> ### /Covers (ignored from GitHub)
> - */New Covers* - folder to download new covers
> - */Fresh Covers to Check* - folder that stores new covers to check manualy

### /Databases
- *AMR_artisitGenres.txt* - list of Artists with Genres for MP3 tags
- *AMR_artisitIDs.csv* - CSV of Artists Apple Music IDs for LookApp
- *AMR_csReleases_DB.csv* - CSV of Coming Soon releases (shown on main HTML)
- *AMR_newReleases_DB.csv* - CSV of New releases (shown on AMR HTMLs)
- *AMR_releases_DB.csv* - CSV of all releases for Artists in "AMR_artisitIDs.csv"

### \Python Notebooks
- *AMR Check Database v.2.024.ipynb* - main
- *AMR Covers Downloader v.2.024.ipynb* - main
- *AMR LookApp v.2.024.ipynb* - main
- *AMR New Releases v.2.024.ipynb* - main
- *requirements.txt* - third party packages for Python 

#### \resources
CSS & ICOs



mushroomoff.github.io/Python Scripts
mushroomoff.github.io/Python Scripts/AMR_CoversDownloader_local.py
mushroomoff.github.io/Python Scripts/AMR_List2Download_local.py
mushroomoff.github.io/Python Scripts/AMR_LookApp_github.py
mushroomoff.github.io/Python Scripts/AMR_LookApp_local.py
mushroomoff.github.io/Python Scripts/AMR_NewReleases_github.py
mushroomoff.github.io/Python Scripts/AMR_NewReleases_local.py
mushroomoff.github.io/Resources
mushroomoff.github.io/Resources/favicon-2.ico
mushroomoff.github.io/Resources/favicon.ico
mushroomoff.github.io/Resources/index.css
mushroomoff.github.io/Resources/styles.css
mushroomoff.github.io/Resources/touch-icon-ipad-retina-2.png
mushroomoff.github.io/Resources/touch-icon-ipad-retina.png
mushroomoff.github.io/Resources/touch-icon-ipad.png
mushroomoff.github.io/Resources/touch-icon-iphone-retina.png
mushroomoff.github.io/Resources/touch-icon-iphone.png

