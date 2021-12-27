docker-compose -f docker-compose.yml up -d
docker exec -it kafka sh -c "\$KAFKA_HOME/bin/kafka-console-producer.sh --broker-list kafka:9093 --topic user_events < data/stream.jsonl"