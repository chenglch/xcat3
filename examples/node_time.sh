#!/bin/bash
count=$1
count=${count:-10}

# create nodes
curl -XPOST 'http://localhost:3010/v1/nodes' -H Content-Type:application/json -d @data.json

for((i=1;i<$count;i++))
do
   curl -XPUT 'http://localhost:3010/v1/nodes/states/power?target=on' -H Content-Type:application/json -d @name.json
done

for((i=1;i<$count;i++))
do
   curl -XGET 'http://localhost:3010/v1/nodes' -H Content-Type:application/json
done

for((i=1;i<$count;i++))
do
   curl -XGET 'http://localhost:3010/v1/nodes/node1' -H Content-Type:application/json
done

# delete nodes
curl -XDELETE 'http://localhost:3010/v1/nodes' -H Content-Type:application/json -d @name.json

