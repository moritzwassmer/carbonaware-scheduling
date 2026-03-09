@echo off
if "%REPO_ROOT%"=="" set "REPO_ROOT=C:\Users\morit\repos\carbonaware-scheduling"

:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete clusters --all
kind create cluster --config="%REPO_ROOT%\kind_conf_3node_1.yml" --name cluster

cd /d "%REPO_ROOT%"

:: Experiment execution
kubectl config use-context kind-cluster
kubectl apply -f "%REPO_ROOT%\rbac.yaml"
kubectl apply -f "%REPO_ROOT%\deployment.yml"

:: only when necessary
cd /d "%REPO_ROOT%"
kubectl cp scheduler:/app/normal_strategy.log "%REPO_ROOT%\results\normal_strategy.log"
kubectl cp scheduler:/app/carbonaware_strategy.log "%REPO_ROOT%\results\carbonaware_strategy.log"

:: other
kubectl exec --stdin --tty shell-demo -- /bin/bash :: ssh
kubectl get nodes
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<node>