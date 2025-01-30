:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete clusters --all
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\cconf_carbonaware.yml --name carbonaware
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\cconf_normal.yml --name normal

cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4

:: Carbonaware execution
kubectl config use-context kind-carbonaware
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment_carbonaware.yml

:: Normal execution
kubectl config use-context kind-normal
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment_normal.yml

:: only when necessary

cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4
kubectl cp scheduler-operator:/app/normal_strategy.log results/normal_strategy.log
kubectl config use-context kind-carbonaware
kubectl cp scheduler-operator:/app/carbonaware_strategy.log results/carbonaware_strategy.log

:: other
kubectl rollout restart deployment kopfexample-operator
kubectl config get-contexts
kubectl exec --stdin --tty shell-demo -- /bin/bash :: ssh


kubectl get nodes
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<node>