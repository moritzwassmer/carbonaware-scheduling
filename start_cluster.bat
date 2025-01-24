cd C:\Users\morit\kind
start kind.exe
kind delete cluster
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\cluster-config.yml

kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yml
kubectl create deployment task4 --image=mowassmer/task4:1.0.1
