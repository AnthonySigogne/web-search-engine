# web-search-engine
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Python 3.5](https://img.shields.io/badge/python-3.5-blue.svg)

A web search engine like Google through an API.
The goal is to index an infinite list of URLs (web pages), and then be able to quickly search relevant URLs against a query. This engine uses the ElasticSearch database.

## Indexing
The indexing operation of a new URL first crawls URL, then extracts the title and main text content from the page.
Then, a new document representing the URL's data is saved in ElasticSearch, and goes for indexing.

## Searching
When searching for relevant URLs, the engine will compare the query with the data of each document (web page), and retrieve a list of URLs matching the query, sorted by relevance.

This search engine works for English, French and German URLs only (language of content).

## INSTALL AND RUN WITH PIP
To install the web search engine, follow these steps :
```
git clone https://github.com/AnthonySigogne/web-search-engine.git
cd web-search-engine
pip install -r requirements.txt
```

Then, run the tool with this command :
```
FLASK_APP=index.py HOST=<ip> PORT=<port> USERNAME=<username> PASSWORD=<password> flask run
```
Where :
- <ip> + <port> is the route to ElasticSearch
- <username> + <password> are credentials to access ElasticSearch

To run in debug mode, prepend *FLASK_DEBUG=1* to the command :
```
FLASK_DEBUG=1 ... flask run
```

To list all services of API, type this endpoint in your web browser : http://localhost:5000/

## INSTALL AND RUN WITH DOCKER
To build this API with Docker :
```
docker build -t web-search-engine .
```

To run the Docker container :
```
docker run -p <port>:5000 \
-e "HOST=<ip>" \
-e "PORT=<port>" \
-e "USERNAME=<username>" \
-e "PASSWORD=<password>" \
web-search-engine
```

## USAGE AND EXAMPLES
