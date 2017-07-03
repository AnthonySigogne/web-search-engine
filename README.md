# web-search-engine
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Python 3.5](https://img.shields.io/badge/python-3.5-blue.svg)

API - a simple web search engine.
The goal is to index an infinite list of URLs (web pages), and then be able to quickly search relevant URLs against a query. This engine uses the ElasticSearch database.

### Indexing
The indexing operation of a new URL first crawls URL, then extracts the title and main text content from the page.
Then, a new document representing the URL's data is saved in ElasticSearch, and goes for indexing.

### Searching
When searching for relevant URLs, the engine will compare the query with the data of each document (web page), and retrieve a list of URLs matching the query, sorted by relevance.

### UI
This search engine can be used with an UI : https://github.com/AnthonySigogne/web-search-engine-ui

### Note
For the moment, this tool works for English, French and German pages only.

## DEMO
A demo can be found here : http://searchengine.byprog.com/  

About 500 French URLs and 500 English URLs of the news network http://www.france24.com/ have been indexed.

## INSTALL AND RUN

### REQUIREMENTS
This tool requires *Python3+* and *ElasticSearch5+*.

### WITH PIP
```
git clone https://github.com/AnthonySigogne/web-search-engine.git
cd web-search-engine
pip install -r requirements.txt
```

Then, run the tool :
```
FLASK_APP=index.py HOST=<ip> PORT=<port> USERNAME=<username> PASSWORD=<password> flask run
```
Where :
* `ip` + `port` : route to ElasticSearch
* `username` + `password` : credentials to access

To run in debug mode, prepend `FLASK_DEBUG=1` to the command :
```
FLASK_DEBUG=1 ... flask run
```

### WITH DOCKER
To run the tool with Docker, you can use my DockerHub image :
https://hub.docker.com/r/anthonysigogne/web-search-engine/
```
docker run -p 5000:5000 \
-e "HOST=<ip>" \
-e "PORT=<port>" \
-e "USERNAME=<username>" \
-e "PASSWORD=<password>" \
anthonysigogne/web-search-engine
```
Where :
* `ip` + `port` : route to ElasticSearch
* `username` + `password` : credentials to access ElasticSearch

Or, build yourself a Docker image :
```
git clone https://github.com/AnthonySigogne/web-search-engine.git
cd web-search-engine
docker build -t web-search-engine .
```

## USAGE AND EXAMPLES
To list all services of API, type this endpoint in your web browser : http://localhost:5000/

### INDEXING
Index a web page through its URL.

* **URL**

  /index

* **Method**

  `POST`

* **Form Data Params**

  **Required:**

  `url=[string]`, the url to index

  `language=[string]` can be `fr`, `en` or `de`

* **Success Response**

  * **Code:** 200 <br />
    **Content:** `Success`


* **Error Response**

  * **Code:** 400 INVALID USAGE <br />


* **Sample Call (with cURL)**

  ```
  curl http://localhost:5000/index --data "language=en&url=https://www.byprog.com/en/"
  ```

### SEARCHING
Query engine to find a list of relevant URLs.
Return the sublist of matching URLs sorted by relevance, and the total of matching URLs, in JSON.

* **URL**

  /search

* **Method**

  `POST`

* **Form Data Params**

  **Required:**

  `query=[string]`, the search query  

  **Not required:**

  `start=[integer]`, the start of hits (0 by default)

  `hits=[integer]`, the number of hits returned by query (10 by default)

* **Success Response**

  * **Code:** 200 <br />
    **Content:**
    ```
    {
      "total": 1,
      "results": [
        {
          "title": "Anthony Sigogne / Freelance / Full-Stack Developer",
          "description": "Full-Stack Developer specialized in new technologies and innovative IT solutions.",
          "url": "https://www.byprog.com/en/"
        }
      ]
    }
    ```


* **Error Response**

  * **Code:** 400 INVALID USAGE <br />


* **Sample Call (with cURL)**

  ```
  curl http://localhost:5000/search --data "query=freelance fullstack"
  ```

## FUTURE FEATURES
* add more languages
* detect automatically the language of web page content
* index more page features like keywords,...
* highlight of matching parts like Google or Bing
* better scoring function
* filter bad results

## LICENCE
MIT
