@echo off
if "%REPO_ROOT%"=="" set "REPO_ROOT=C:\Users\morit\repos\carbonaware-scheduling"

:: start kind
cd C:\Users\morit\kind
start kind.exe

:: cleanup then create clusters
kind delete clusters --all
kind create cluster --config="%REPO_ROOT%\kind_conf_3node_1.yml" --name carbonaware
kind create cluster --config="%REPO_ROOT%\kind_conf_3node_2.yml" --name normal

cd /d "%REPO_ROOT%"

:: Carbonaware execution
kubectl config use-context kind-carbonaware
kubectl apply -f "%REPO_ROOT%\rbac.yaml"
kubectl apply -f "%REPO_ROOT%\deployment_carbonaware.yml"

:: Normal execution
kubectl config use-context kind-normal
kubectl apply -f "%REPO_ROOT%\rbac.yaml"
kubectl apply -f "%REPO_ROOT%\deployment_normal.yml"

:: only when necessary

cd /d "%REPO_ROOT%"
kubectl cp scheduler:/app/normal_strategy.log "%REPO_ROOT%\results\normal_strategy.log"
kubectl config use-context kind-carbonaware
kubectl cp scheduler:/app/carbonaware_strategy.log "%REPO_ROOT%\results\carbonaware_strategy.log"

:: other
kubectl config get-contexts
kubectl exec --stdin --tty shell-demo -- /bin/bash :: ssh


kubectl get nodes
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<node>