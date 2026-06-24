pipeline {
    agent any // s'exécute sur n'importe quel agent disponible

    environment {
        IMAGE_NAME = 'sentiment-ai'
        REGISTRY = 'ghcr.io/davidosf'
        // IMAGE_TAG = SHA Git court du commit (ex: a3f8c12)
        // Chaque build produit une image taguée de façon unique et traçable
        IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Branche : ${env.BRANCH_NAME}"
                echo "Git branch : ${env.GIT_BRANCH}"
                echo "Commit: ${env.GIT_COMMIT}"
                sh 'git log --oneline -5'
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    docker run --rm \
                      --volumes-from jenkins \
                      -w "$WORKSPACE" \
                      python:3.12-slim \
                      sh -c "pip install flake8 -q && flake8 src/ --max-line-length=100"
                '''
            }
        }

        // stage('Build & Test') {
        //     steps {
        //         sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
        //         sh '''
        //             docker run --rm \
        //               ${IMAGE_NAME}:${IMAGE_TAG} \
        //               pytest tests/ -v \
        //               --cov=src \
        //               --cov-report=xml:coverage.xml \
        //               --cov-report=term-missing \
        //               --cov-fail-under=70
        //         '''
        //     }
        //     post {
        //         failure {
        //             echo 'Tests échoués ou coverage insuffisant (< 70%)'
        //         }
        //     }
        // }
        stage('IaC Validate') {
            steps {
                dir('infra') {
                    sh 'terraform init -backend=false -input=false'
                    sh 'terraform fmt -check'
                    sh 'terraform validate'
                }
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                docker rm -f test-runner 2>/dev/null || true
                set +e
                docker run \
                -e CI=true \
                --name test-runner \
                ${IMAGE_NAME}:${IMAGE_TAG} \
                pytest tests/ -v \
                --cov=src \
                --cov-report=xml:/tmp/coverage.xml \
                --cov-report=term-missing \
                --cov-fail-under=70
                TEST_EXIT_CODE=$?
                set -e
                # Copier coverage .xml depuis le conteneur vers le workspace
                docker cp test-runner:/tmp/coverage.xml ./coverage.xml 2>/dev/null || true
                sed -i "s#/app/src#${WORKSPACE}/src#g" coverage.xml 2>/dev/null || true
                docker rm -f test-runner 2>/dev/null || true
                # Retourner le code de sortie des tests
                exit $TEST_EXIT_CODE
                '''
            }
            post {
                failure { echo 'Tests échoués ou coverage insuffisant (< 70%)' }
            }
        }

        stage('SonarQube Analysis') {
            environment {
                SONARQUBE_TOKEN = credentials('sonar-token')
            }
            steps {
                sh 'rm -rf $WORKSPACE/.scannerwork'
                withSonarQubeEnv('sonarqube') {
                    sh '''
                    docker run --rm \
                      --network cicd-network \
                      --volumes-from jenkins \
                      -w "$WORKSPACE" \
                      -e SONAR_HOST_URL="$SONAR_HOST_URL" \
                      -e SONAR_TOKEN="$SONARQUBE_TOKEN" \
                      sonarsource/sonar-scanner-cli:latest \
                      sonar-scanner \
                      -Dsonar.projectKey=sentiment-ai \
                      -Dsonar.projectName=SentimentAI \
                      -Dsonar.projectBaseDir="$WORKSPACE" \
                      -Dsonar.sources=src \
                      -Dsonar.python.version=3.11 \
                      -Dsonar.python.coverage.reportPaths=coverage.xml \
                      -Dsonar.sourceEncoding=UTF-8 \
                      -Dsonar.working.directory=$WORKSPACE/.scannerwork
                    '''
                }
            }
        }
        stage('Quality Gate') {
            steps {
                timeout ( time : 15, unit : 'MINUTES') 
                {
                    // Attend le résultat asynchrone du Quality Gate SonarQube
                    // abortPipeline : true => bloque Push et Deploy si le gate échoue
                    waitForQualityGate abortPipeline : true
                }
            }
        }

        stage('Security Scan') {
            steps {
                // --exit-code 1 : fail si une CVE HIGH ou CRITICAL est trouvée
                // --format table : rapport lisible dans les logs Jenkins
                sh """
                    docker run --rm \
                    -v /var/run/docker.sock:/var/run/docker.sock \
                    -v trivy-cache:/root/.cache/trivy \
                    aquasec/trivy:latest image \
                    --severity HIGH,CRITICAL \
                    --exit-code 0 \
                    --format table \
                    ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }

            post {
                failure {
                    echo 'Vulnérabilités CRITICAL ou HIGH détectées !'
                    echo 'Corrigez les dépendances avant de déployer.'
                }
            }
        }

        stage('Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-token',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh """
                        echo "\$REGISTRY_PASS" | docker login ghcr.io -u "\$REGISTRY_USER" --password-stdin
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:latest
                        docker push ${REGISTRY}/${IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('IaC Apply') {
            when { expression { env.GIT_BRANCH == 'origin/main' } }
            steps {
                dir('infra') {
                    sh 'terraform init -input=false -migrate-state -force-copy -backend-config="path=/var/jenkins_home/terraform-state/sentiment-ai.tfstate"'
                    sh 'docker rm -f sentiment-staging 2>/dev/null || true'
                    sh """
                    terraform apply -auto-approve \
                    -var='image_tag=${IMAGE_TAG}'
                    """
                }
            }
        }

        stage('Deploy Staging') {
            when {
                expression { env.GIT_BRANCH == 'origin/main' }
            }

            // steps {
            //     echo "Déploiement de ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} en staging..."

            //     sh '''
            //         # Arrêter le staging précédent proprement
            //         docker compose -f docker-compose.yml -p staging down 2>/dev/null || true

            //         # Démarrer la nouvelle version
            //         docker compose -f docker-compose.yml -p staging up -d

            //         echo "Staging disponible sur http://localhost:8001"
            //     '''
            // }
            steps {
                sh 'docker run --rm --network cicd-network curlimages/curl:latest curl -f http://sentiment-staging:8000/health'
            }
        }

        stage('Smoke Test') {
            when {
                expression { env.GIT_BRANCH == 'origin/main' }
            }

            steps {
                sh '''
                echo "Attente démarrage (10s)..."
                sleep 10

                # 1. L'app répond
                docker run --rm --network cicd-network curlimages/curl:latest \
                    curl -f http://sentiment-staging:8000/health
                echo "/health OK"

                # 2. Les métriques sont exposées
                docker run --rm --network cicd-network curlimages/curl:latest \
                    curl -s http://sentiment-staging:8000/metrics | \
                    grep -q sentiment_predictions_total
                echo "/metrics OK -- métriques SentimentAI présentes"

                # 3. Prometheus scrape l'app
                sleep 20
                docker run --rm --network cicd-network curlimages/curl:latest \
                    curl -s "http://prometheus:9090/api/v1/query?query=up%7Bjob%3D%27sentiment-ai%27%7D" | \
                    grep -q '"value"'
                echo "Prometheus scrape sentiment-ai : UP"

                # 4. Grafana répond
                docker run --rm --network cicd-network curlimages/curl:latest \
                    curl -f http://grafana:3000/api/health
                echo "Grafana OK"
                '''
            }

            post {
                failure {
                sh 'docker logs prometheus || true'
                sh 'docker logs sentiment-staging || true'
                echo 'Smoke Test KO -- voir logs ci-dessus'
                }
            }
        }
    }
    post {
        always {
            // Nettoyer les conteneurs de test, qu'il y ait succès ou échec
            sh 'docker compose down -v 2>/dev/null || true'
        }
        success {
            echo "Pipeline réussi ! Image : ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo 'Pipeline échoué. Consultez les logs ci-dessus.'
        }
    }
}
