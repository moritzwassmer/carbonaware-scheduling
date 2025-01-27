:: clean up docker state
::FOR /f "tokens=*" %i IN ('docker ps -q') DO docker stop %i :: stop all running containers
::FOR /f "tokens=*" %i IN ('docker ps -a') DO docker rm %i :: remove all containers
::FOR /f "tokens=*" %i in ('docker images kindest/node -q') DO docker rmi %i :: remove all kind images

:: start kind
cd C:\Users\morit\kind
start kind.exe

:: create cluster
kind delete cluster
kind create cluster --config=C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\3_nodes_cluster_config.yml

:: build and push image TODO do manually
cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4

::docker build --pull --rm --no-cache -f dockerfile.Dockerfile -t task4:1.0.1 .
::docker login
::docker image push docker.io/mowassmer/task4:1.0.1 

:: apply k8s resources
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\rbac.yaml
kubectl apply -f C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4\deployment.yml

:: only when necessary
cd C:\Users\morit\OneDrive\UNI\Master\WS24\CC\Assignments\4
kubectl cp kopfexample-operator-5d878f47c4-lqbx8:/app/scheduler.log results/scheduler.log
kubectl rollout restart deployment kopfexample-operator
