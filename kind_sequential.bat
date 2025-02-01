:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete clusters --all
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\kind_conf_3node_1.yml --name cluster

cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4

:: Experiment execution
kubectl config use-context kind-cluster
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yaml

:: only when necessary
cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4
kubectl cp scheduler:/app/normal_strategy.log results/normal_strategy.log
kubectl cp scheduler:/app/carbonaware_strategy.log results/carbonaware_strategy.log

:: other
kubectl exec --stdin --tty shell-demo -- /bin/bash :: ssh
kubectl get nodes
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<node>