#!/bin/sh
set -e

CONNECT_URL="http://debezium:8083"
CONNECTOR_FILE="/debezium/freight-connector.json"

echo "Waiting for Kafka Connect to be ready..."
until curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; do
  echo "  Kafka Connect not ready yet, retrying in 5s..."
  sleep 5
done
echo "Kafka Connect is ready."

EXISTING=$(curl -s "${CONNECT_URL}/connectors" | grep -c "freight-postgres-connector" || true)
if [ "$EXISTING" -gt "0" ]; then
  echo "Connector already registered, skipping."
  exit 0
fi

echo "Registering freight Postgres connector..."
curl -i -X POST \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  "${CONNECT_URL}/connectors" \
  -d @"${CONNECTOR_FILE}"

echo ""
echo "Connector registered successfully."
