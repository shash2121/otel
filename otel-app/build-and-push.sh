#!/bin/bash
set -e

REGISTRY="${DOCKER_REGISTRY:-sha2121}"
PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"

echo "Building service-a (${PLATFORM})..."
docker buildx build --platform "${PLATFORM}" \
  -t "${REGISTRY}/service-a:latest" service-a/ --push

echo "Building service-b (${PLATFORM})..."
docker buildx build --platform "${PLATFORM}" \
  -t "${REGISTRY}/service-b:latest" service-b/ --push

echo "Done. Images pushed:"
echo "  ${REGISTRY}/service-a:latest"
echo "  ${REGISTRY}/service-b:latest"
