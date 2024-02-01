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

