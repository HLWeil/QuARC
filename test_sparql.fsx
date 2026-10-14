let server = "http://localhost:3030/ds/query"
let server2 = "192.52.43.238:3030/ds/query"

let baseQueryString = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

let personQueryString = """PREFIX schema: <http://schema.org/>

SELECT ?person ?property ?value
WHERE {
  ?person a schema:Person ;
          ?property ?value .
}
ORDER BY ?person ?property
"""

let studyNamesQueryString = """PREFIX schema: <http://schema.org/>

SELECT ?identifier
WHERE {
  ?study a schema:Dataset ;
          schema:additionalType "Study" ;
          schema:identifier ?identifier .
}
"""


#r "nuget: FsHttp"

open FsHttp


http {
    GET server
    query [
        "query", studyNamesQueryString
    ]
    headers [
        "Accept", "application/sparql-results+json"
    ]
}
|> Request.send
|> Response.toText

1+1
