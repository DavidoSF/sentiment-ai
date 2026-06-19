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

        stage ('Build & Test') {
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
                docker rm -f test-runner 2>/dev/null || true
                # Retourner le code de sortie des tests
                exit $TEST_EXIT_CODE
                '''
            }
            post {
                failure { echo 'Tests échoués ou coverage insuffisant (< 70%)' }
            }
        }

        stage ('SonarQube Analysis') {
            environment {
                SONARQUBE_TOKEN = credentials ('sonar-token')
            }
            steps {
                withSonarQubeEnv ('sonarqube') {
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
                        -Dsonar.sourceEncoding=UTF-8
                    '''
                }
            }
        }
        stage ('Quality Gate') {
            steps {
                timeout ( time : 15, unit : 'MINUTES') 
                {
                    // Attend le résultat asynchrone du Quality Gate SonarQube
                    // abortPipeline : true => bloque Push et Deploy si le gate échoue
                    waitForQualityGate abortPipeline : true
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
