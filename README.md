# Paper of the Day

One research paper a day from [arXiv](https://arxiv.org), per topic. A GitHub Actions workflow picks
today's paper every morning and publishes it to GitHub Pages.

## Run it locally

```
python paper_of_the_day.py                 # today's paper for the default topic
python paper_of_the_day.py --new           # swap today's paper for a different one
python paper_of_the_day.py --all --build-site   # every topic, then write site/index.html
```

## Add a topic

Add an entry to `topics.json` with a name and a list of
[arXiv category codes](https://arxiv.org/category_taxonomy), for example:

```json
"machine-learning": {
  "name": "Machine Learning",
  "description": "New ideas in ML.",
  "categories": ["cs.LG", "stat.ML"]
}
```

The next daily run adds it to the web page.
