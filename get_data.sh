mkdir data
curl http://tx.tamedia.ch.s3.amazonaws.com/challenge/data/stream.jsonl.gz -o data/stream.jsonl.gz
gunzip -k -f data/stream.jsonl.gz