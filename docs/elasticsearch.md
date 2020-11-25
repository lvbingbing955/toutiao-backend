```http
// 文章索引
curl -X PUT 172.17.0.135:9200/articles -H 'Content-Type: application/json' -d'
{
   "settings" : {
   		"index": {
            "number_of_shards" : 3,
      		"number_of_replicas" : 1
   		}
   }
}
'
```

```http
curl -X PUT 172.17.0.135:9200/articles/_mapping/article -H 'Content-Type: application/json' -d'
{
           "_all": {
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_max_word",
                "term_vector": "no",
                "store": "false"
            },
            "properties": {
                "article_id": {
                    "type": "long",
                    "store": "false",
                    "include_in_all": "false"
                },
                "user_id": {
                  	"type": "long",
                    "store": "false",
                    "include_in_all": "false"
                },
                "title": {
                    "type": "text",
                    "store": "false",
                    "term_vector": "with_positions_offsets",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_max_word",
                    "include_in_all": "true",
                    "boost": 2
                },
                "content": {
                    "type": "text",
                    "store": "false",
                    "term_vector": "with_positions_offsets",
                    "analyzer": "ik_max_word",
                    "include_in_all": "true"
                },
                "status": {
                    "type": "byte",
                    "store": "false",
                    "include_in_all": "false"
                },
                "create_time": {
                    "type": "date",
                    "store": "false",
                    "include_in_all": "false"
                }
            }

}
'
```



```http
// 搜索词补全
curl -X PUT 172.17.0.135:9200/completions -H 'Content-Type: application/json' -d'
{
   "settings" : {
   		"index": {
            "number_of_shards" : 3,
      		"number_of_replicas" : 1
   		}
   }
}
'


```

```http
curl -X PUT 172.17.0.135:9200/completions/_mapping/words -H 'Content-Type: application/json' -d'
{
       "words": {
            "properties": {
                "suggest": {
                    "type": "completion",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_max_word"
                }
            }
       }
}
'


```







```http
curl -XGET 172.17.0.135:9200/articles/article/_search?pretty -d '
{
	"_source": ["title"],
	"query": {
		"bool": {
            "must": [
                {"match": {"_all": "python flask"}}
            ],
            "filter": [
                {"term": {"status": {"value":2}}}
            ]
		}
	}
}
'

```

```http
curl 172.17.0.135:9200/_analyze?pretty -d '
{
	"analyzer": "ik_max_word",
    "text": "python flask"
}
'


```

```http
curl 172.17.0.135:9200/articles/article/_search?pretty -d '
{
	"explain": true,
	"query": {
		"bool": {
            "must": [
                {"match": {"_all": "python flask"}}
            ],
            "filter": [
                {"term": {"status": {"value":2}}}
            ]
		}
	}
}
'

```



```http
curl 172.17.0.135:9200/articles/article/_search?pretty -d '
{
    "suggest": {
        "title-suggest" : {
            "prefix" : "pyth", 
            "completion" : { 
                "field" : "title" 
            }
        }
    }
}
'
```



```http
curl 172.17.0.135:9200/articles/_count?pretty
```



```shell
cd /usr/share/logstash/bin/
./logstash -f /root/logstash_mysql_es_completion.conf
```



```http
curl -X GET 172.17.0.135:9200/articles/article/_search?pretty -d '
{
	"_source": ["title", "user_id"],
    "query":{
        "bool": {
            "must": [
                {"match": {"_all": "python flask"}}
            ],
            "filter": [
                {"term": {"user_id": {"value": 1}}}
            ],
            "must_not": [
                {"term": {"status": {"value": 4}}}
            ]
        }
    }
}'
```

