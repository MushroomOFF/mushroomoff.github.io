# TestRepo
This repo is only for some tests

Trying to understand GitHub Actions:
https://www.python-engineer.com/posts/run-python-github-actions/

# Index
#### root
index.html
#### AMRs
HTMLs for each month with new releases
#### Databases
CSV with all parsed new releases 
#### Python
*AMR_NewReleases.py* - main Python script to collect new releases

*requirements.txt* - third party packages for Python 
#### resources
CSS & ICOs

# ideas

https://github.com/actions/checkout/tree/main

## Checkout multiple repos (side by side)

```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    path: main

- name: Checkout tools repo
  uses: actions/checkout@v4
  with:
    repository: my-org/my-tools
    path: my-tools
```

> If your secondary repository is private you will need to add the option noted in Checkout multiple repos (private)

## Checkout multiple repos (private)

```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    path: main

- name: Checkout private tools
  uses: actions/checkout@v4
  with:
    repository: my-org/my-private-tools
    token: ${{ secrets.GH_PAT }} # `GH_PAT` is a secret that contains your PAT
    path: my-tools
```

> - `${{ github.token }}` is scoped to the current repository, so if you want to checkout a different repository that is private you will need to provide your own [PAT](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line).

# Another idea:

https://github.com/ad-m/github-push-action



mushroomoff.github.io
mushroomoff.github.io/AMRs
mushroomoff.github.io/AMRs/AMR 2022-12.html
mushroomoff.github.io/AMRs/AMR 2023-01.html
mushroomoff.github.io/AMRs/AMR 2023-02.html
mushroomoff.github.io/AMRs/AMR 2023-03.html
mushroomoff.github.io/AMRs/AMR 2023-04.html
mushroomoff.github.io/AMRs/AMR 2023-05.html
mushroomoff.github.io/AMRs/AMR 2023-06.html
mushroomoff.github.io/AMRs/AMR 2023-07.html
mushroomoff.github.io/AMRs/AMR 2023-08.html
mushroomoff.github.io/AMRs/AMR 2023-09.html
mushroomoff.github.io/AMRs/AMR 2023-10.html
mushroomoff.github.io/AMRs/AMR 2023-11.html
mushroomoff.github.io/AMRs/AMR 2023-12.html
mushroomoff.github.io/AMRs/AMR 2024-01.html
mushroomoff.github.io/AMRs/AMR 2024-02.html
mushroomoff.github.io/AMRs/AMR 2024-03.html
mushroomoff.github.io/Covers
mushroomoff.github.io/Covers/New Covers
mushroomoff.github.io/Covers/Fresh Covers to Check
mushroomoff.github.io/Databases
mushroomoff.github.io/Databases/AMR_artisitGenres.txt
mushroomoff.github.io/Databases/AMR_artisitIDs.csv
mushroomoff.github.io/Databases/AMR_csReleases_DB.csv
mushroomoff.github.io/Databases/AMR_newReleases_DB.csv
mushroomoff.github.io/Databases/AMR_releases_DB.csv
mushroomoff.github.io/Python Notebooks
mushroomoff.github.io/Python Notebooks/AMR Check Database v.2.024.ipynb
mushroomoff.github.io/Python Notebooks/AMR Covers Downloader v.2.024.ipynb
mushroomoff.github.io/Python Notebooks/AMR LookApp v.2.024.ipynb
mushroomoff.github.io/Python Notebooks/AMR New Releases v.2.024.ipynb
mushroomoff.github.io/Python Notebooks/requirements.txt
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
mushroomoff.github.io/index.html
mushroomoff.github.io/README.md
mushroomoff.github.io/status.log