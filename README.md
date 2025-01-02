# Deploy Containerized version to Azure Container Apps
(Basic instructions, many details missing atm)

- To build the container (For Azure deployment):
docker build --tag comprendo-api --platform linux/arm64 .

- Push to ACR
docker tag comprendo-api comprendocr.azurecr.io/comprendo-api
docker push comprendocr.azurecr.io/comprendo-api

- Later define and create the container app from this image.