:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete cluster --name cluster-carbonaware
kind delete cluster --name cluster-normal
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\3_nodes_cluster_config.yml --name cluster-carbonaware
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\3_nodes_cluster_config2.yml --name cluster-normal

cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4

:: Carbonaware execution
kubectl config use-context kind-cluster-carbonaware
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yml

:: Normal execution
kubectl config use-context kind-cluster-normal
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yml