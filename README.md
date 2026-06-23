python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload


docker ps

docker logs fastapi-local-test
docker images | grep fastapi


Cleanup:
docker stop fastapi-local-test
docker rm fastapi-local-test
docker rmi -f fastapi:local

Minikube:
minikube -p ckad-docker image load fastapi:local --overwrite=true
minikube -p ckad-docker image ls | grep fastapi
minikube -p ckad-docker image rm fastapi:local
minikube -p ckad-docker service api-service -n lab-pack --url

Kubectl
kubectl rollout restart deployment backend-fastapi


Test:
curl http://127.0.0.1:8000/healthz


kubectl rollout restart deployment/coredns -n kube-system
kubectl rollout restart daemonset/kindnet -n kube-system
kubelctl logs -n kube-system -l k8s-app=kube-dns -c coredns


# The Complete Dual-Tunnel Dev Fleet
kubectl port-forward deployment/ingress-nginx-controller 8080:80 -n ingress-nginx > /dev/null 2>&1 & \
kubectl port-forward statefulset/postgres 5435:5432 -n lab-pack > /dev/null 2>&1 &