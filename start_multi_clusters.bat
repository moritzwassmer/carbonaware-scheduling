:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete clusters --all
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\cconf_carbonaware.yml --name cluster-carbonaware
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\cconf_normal.yml --name cluster-normal

cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4

:: Carbonaware execution
kubectl config use-context kind-cluster-carbonaware
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yml

:: Normal execution
kubectl config use-context kind-cluster-normal
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment_normal.yml

:: only when necessary

kubectl cp :/app/normal_strategy.log results/normal_strategy.log
kubectl config use-context kind-cluster-carbonaware
kubectl cp :/app/carbonaware_strategy.log results/carbonaware_strategy.log
kubectl rollout restart deployment kopfexample-operator

kubectl config get-contexts