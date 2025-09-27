pipeline {
    agent any
    
    environment {
        // Docker and Registry Configuration
        DOCKER_REGISTRY = 'your-registry.com'
        DOCKER_NAMESPACE = 'ecommerce'
        
        // Application Configuration
        PRODUCT_SERVICE_IMAGE = "${DOCKER_NAMESPACE}/product-service"
        ORDER_SERVICE_IMAGE = "${DOCKER_NAMESPACE}/order-service"
        FRONTEND_IMAGE = "${DOCKER_NAMESPACE}/frontend"
        
        // Database Configuration
        POSTGRES_HOST = 'postgres-test'
        POSTGRES_USER = 'postgres'
        POSTGRES_PASSWORD = 'postgres'
        PRODUCT_DB_NAME = 'products'
        ORDER_DB_NAME = 'orders'
        
        // Azure Configuration (for production)
        AZURE_STORAGE_ACCOUNT_NAME = credentials('azure-storage-account-name')
        AZURE_STORAGE_ACCOUNT_KEY = credentials('azure-storage-account-key')
        AZURE_STORAGE_CONTAINER_NAME = 'product-images'
        
        // SonarQube Configuration
        SONAR_TOKEN = credentials('sonar-token')
        SONAR_HOST_URL = 'http://sonarqube:9000'
        
        // Test Environment URLs
        TEST_PRODUCT_SERVICE_URL = 'http://product-service-test:8000'
        TEST_ORDER_SERVICE_URL = 'http://order-service-test:8000'
        TEST_FRONTEND_URL = 'http://frontend-test:80'
        
        // Production Environment URLs
        PROD_PRODUCT_SERVICE_URL = 'http://product-service-prod:8000'
        PROD_ORDER_SERVICE_URL = 'http://order-service-prod:8000'
        PROD_FRONTEND_URL = 'http://frontend-prod:80'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    env.BUILD_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
                }
            }
        }
        
        stage('Build') {
            parallel {
                stage('Build Product Service') {
                    steps {
                        echo 'Building Product Service Docker image...'
                        script {
                            def productImage = docker.build(
                                "${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}",
                                "-f backend/product_service/Dockerfile backend/product_service"
                            )
                            env.PRODUCT_SERVICE_IMAGE_ID = productImage.id
                        }
                    }
                }
                
                stage('Build Order Service') {
                    steps {
                        echo 'Building Order Service Docker image...'
                        script {
                            def orderImage = docker.build(
                                "${ORDER_SERVICE_IMAGE}:${BUILD_TAG}",
                                "-f backend/order_service/Dockerfile backend/order_service"
                            )
                            env.ORDER_SERVICE_IMAGE_ID = orderImage.id
                        }
                    }
                }
                
                stage('Build Frontend') {
                    steps {
                        echo 'Building Frontend Docker image...'
                        script {
                            def frontendImage = docker.build(
                                "${FRONTEND_IMAGE}:${BUILD_TAG}",
                                "-f frontend/Dockerfile frontend"
                            )
                            env.FRONTEND_IMAGE_ID = frontendImage.id
                        }
                    }
                }
            }
            post {
                success {
                    echo 'All Docker images built successfully!'
                    archiveArtifacts artifacts: '**/Dockerfile', fingerprint: true
                }
                failure {
                    echo 'Docker build failed!'
                }
            }
        }
        
        stage('Test') {
            parallel {
                stage('Unit Tests - Product Service') {
                    steps {
                        echo 'Running Product Service unit tests...'
                        script {
                            docker.image("${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}").inside('-v /var/run/docker.sock:/var/run/docker.sock') {
                                sh '''
                                    cd /app
                                    python -m pytest tests/ -v --tb=short --junitxml=test-results-product.xml --cov=app --cov-report=xml --cov-report=html
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: '**/test-results-product.xml'
                            publishCoverage adapters: [
                                coberturaAdapter('**/coverage.xml')
                            ], sourceFileResolver: sourceFiles('STORE_LAST_BUILD')
                        }
                    }
                }
                
                stage('Unit Tests - Order Service') {
                    steps {
                        echo 'Running Order Service unit tests...'
                        script {
                            docker.image("${ORDER_SERVICE_IMAGE}:${BUILD_TAG}").inside('-v /var/run/docker.sock:/var/run/docker.sock') {
                                sh '''
                                    cd /app
                                    python -m pytest tests/ -v --tb=short --junitxml=test-results-order.xml --cov=app --cov-report=xml --cov-report=html
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: '**/test-results-order.xml'
                            publishCoverage adapters: [
                                coberturaAdapter('**/coverage.xml')
                            ], sourceFileResolver: sourceFiles('STORE_LAST_BUILD')
                        }
                    }
                }
                
                stage('Integration Tests') {
                    steps {
                        echo 'Running integration tests...'
                        script {
                            // Start test environment
                            sh '''
                                docker-compose -f docker-compose.test.yml up -d
                                sleep 30  # Wait for services to be ready
                            '''
                            
                            // Run integration tests
                            sh '''
                                docker run --rm --network ecommerce_test_network \\
                                    -e PRODUCT_SERVICE_URL=http://product-service-test:8000 \\
                                    -e ORDER_SERVICE_URL=http://order-service-test:8000 \\
                                    ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG} \\
                                    python -m pytest tests/integration/ -v --junitxml=integration-test-results.xml
                            '''
                        }
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: '**/integration-test-results.xml'
                            sh 'docker-compose -f docker-compose.test.yml down -v'
                        }
                    }
                }
            }
        }
        
        stage('Code Quality') {
            parallel {
                stage('SonarQube Analysis - Product Service') {
                    steps {
                        echo 'Running SonarQube analysis for Product Service...'
                        script {
                            docker.image("${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}").inside() {
                                sh '''
                                    cd /app
                                    sonar-scanner \\
                                        -Dsonar.projectKey=ecommerce-product-service \\
                                        -Dsonar.sources=. \\
                                        -Dsonar.host.url=${SONAR_HOST_URL} \\
                                        -Dsonar.login=${SONAR_TOKEN} \\
                                        -Dsonar.python.coverage.reportPaths=coverage.xml \\
                                        -Dsonar.python.xunit.reportPath=test-results-product.xml
                                '''
                            }
                        }
                    }
                }
                
                stage('SonarQube Analysis - Order Service') {
                    steps {
                        echo 'Running SonarQube analysis for Order Service...'
                        script {
                            docker.image("${ORDER_SERVICE_IMAGE}:${BUILD_TAG}").inside() {
                                sh '''
                                    cd /app
                                    sonar-scanner \\
                                        -Dsonar.projectKey=ecommerce-order-service \\
                                        -Dsonar.sources=. \\
                                        -Dsonar.host.url=${SONAR_HOST_URL} \\
                                        -Dsonar.login=${SONAR_TOKEN} \\
                                        -Dsonar.python.coverage.reportPaths=coverage.xml \\
                                        -Dsonar.python.xunit.reportPath=test-results-order.xml
                                '''
                            }
                        }
                    }
                }
            }
            post {
                success {
                    echo 'Code quality analysis completed successfully!'
                }
                failure {
                    echo 'Code quality analysis failed!'
                }
            }
        }
        
        stage('Security') {
            parallel {
                stage('Container Security Scan') {
                    steps {
                        echo 'Running Trivy security scan on Docker images...'
                        script {
                            sh '''
                                # Install Trivy if not present
                                if ! command -v trivy &> /dev/null; then
                                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
                                fi
                                
                                # Scan all images
                                trivy image --format json --output trivy-report.json ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}
                                trivy image --format json --output trivy-report-order.json ${ORDER_SERVICE_IMAGE}:${BUILD_TAG}
                                trivy image --format json --output trivy-report-frontend.json ${FRONTEND_IMAGE}:${BUILD_TAG}
                                
                                # Generate HTML reports
                                trivy image --format template --template "@contrib/html.tpl" --output trivy-report.html ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}
                            '''
                        }
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: '.',
                                reportFiles: 'trivy-report.html',
                                reportName: 'Trivy Security Report'
                            ])
                            archiveArtifacts artifacts: 'trivy-report*.json', fingerprint: true
                        }
                    }
                }
                
                stage('Python Security Scan') {
                    steps {
                        echo 'Running Bandit security scan on Python code...'
                        script {
                            docker.image("${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}").inside() {
                                sh '''
                                    cd /app
                                    # Install bandit
                                    pip install bandit
                                    
                                    # Run bandit scan
                                    bandit -r . -f json -o bandit-report.json || true
                                    bandit -r . -f html -o bandit-report.html || true
                                '''
                            }
                        }
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: '.',
                                reportFiles: 'bandit-report.html',
                                reportName: 'Bandit Security Report'
                            ])
                            archiveArtifacts artifacts: 'bandit-report.json', fingerprint: true
                        }
                    }
                }
            }
        }
        
        stage('Deploy to Test') {
            steps {
                echo 'Deploying to test environment...'
                script {
                    // Tag images for test environment
                    sh '''
                        docker tag ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG} ${PRODUCT_SERVICE_IMAGE}:test
                        docker tag ${ORDER_SERVICE_IMAGE}:${BUILD_TAG} ${ORDER_SERVICE_IMAGE}:test
                        docker tag ${FRONTEND_IMAGE}:${BUILD_TAG} ${FRONTEND_IMAGE}:test
                    '''
                    
                    // Deploy to test environment
                    sh '''
                        # Update docker-compose.test.yml with new image tags
                        sed -i "s|image: .*product-service.*|image: ${PRODUCT_SERVICE_IMAGE}:test|g" docker-compose.test.yml
                        sed -i "s|image: .*order-service.*|image: ${ORDER_SERVICE_IMAGE}:test|g" docker-compose.test.yml
                        sed -i "s|image: .*frontend.*|image: ${FRONTEND_IMAGE}:test|g" docker-compose.test.yml
                        
                        # Deploy to test environment
                        docker-compose -f docker-compose.test.yml up -d
                        
                        # Wait for services to be healthy
                        sleep 30
                        
                        # Run health checks
                        curl -f http://localhost:8000/health || exit 1  # Product Service
                        curl -f http://localhost:8001/health || exit 1  # Order Service
                        curl -f http://localhost:3000/ || exit 1        # Frontend
                    '''
                }
            }
            post {
                success {
                    echo 'Test deployment successful!'
                    // Send notification to team
                    emailext (
                        subject: "Test Deployment Successful - Build ${BUILD_NUMBER}",
                        body: "The application has been successfully deployed to the test environment.\n\nBuild: ${BUILD_NUMBER}\nCommit: ${GIT_COMMIT_SHORT}\nTest URLs:\n- Product Service: ${TEST_PRODUCT_SERVICE_URL}\n- Order Service: ${TEST_ORDER_SERVICE_URL}\n- Frontend: ${TEST_FRONTEND_URL}",
                        to: "dev-team@company.com"
                    )
                }
                failure {
                    echo 'Test deployment failed!'
                    emailext (
                        subject: "Test Deployment Failed - Build ${BUILD_NUMBER}",
                        body: "The test deployment has failed. Please check the Jenkins logs for details.\n\nBuild: ${BUILD_NUMBER}\nCommit: ${GIT_COMMIT_SHORT}",
                        to: "dev-team@company.com"
                    )
                }
            }
        }
        
        stage('Release to Production') {
            when {
                branch 'main'
            }
            steps {
                echo 'Releasing to production environment...'
                script {
                    // Tag images for production
                    sh '''
                        docker tag ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG} ${PRODUCT_SERVICE_IMAGE}:latest
                        docker tag ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG} ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}
                        docker tag ${ORDER_SERVICE_IMAGE}:${BUILD_TAG} ${ORDER_SERVICE_IMAGE}:latest
                        docker tag ${ORDER_SERVICE_IMAGE}:${BUILD_TAG} ${ORDER_SERVICE_IMAGE}:${BUILD_TAG}
                        docker tag ${FRONTEND_IMAGE}:${BUILD_TAG} ${FRONTEND_IMAGE}:latest
                        docker tag ${FRONTEND_IMAGE}:${BUILD_TAG} ${FRONTEND_IMAGE}:${BUILD_TAG}
                    '''
                    
                    // Push to registry
                    sh '''
                        docker push ${PRODUCT_SERVICE_IMAGE}:latest
                        docker push ${PRODUCT_SERVICE_IMAGE}:${BUILD_TAG}
                        docker push ${ORDER_SERVICE_IMAGE}:latest
                        docker push ${ORDER_SERVICE_IMAGE}:${BUILD_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                        docker push ${FRONTEND_IMAGE}:${BUILD_TAG}
                    '''
                    
                    // Deploy to production
                    sh '''
                        # Update production docker-compose
                        sed -i "s|image: .*product-service.*|image: ${PRODUCT_SERVICE_IMAGE}:latest|g" docker-compose.prod.yml
                        sed -i "s|image: .*order-service.*|image: ${ORDER_SERVICE_IMAGE}:latest|g" docker-compose.prod.yml
                        sed -i "s|image: .*frontend.*|image: ${FRONTEND_IMAGE}:latest|g" docker-compose.prod.yml
                        
                        # Deploy to production
                        docker-compose -f docker-compose.prod.yml up -d
                        
                        # Wait for services to be healthy
                        sleep 60
                        
                        # Run production health checks
                        curl -f http://prod-server:8000/health || exit 1  # Product Service
                        curl -f http://prod-server:8001/health || exit 1  # Order Service
                        curl -f http://prod-server:3000/ || exit 1        # Frontend
                    '''
                }
            }
            post {
                success {
                    echo 'Production release successful!'
                    emailext (
                        subject: "Production Release Successful - Build ${BUILD_NUMBER}",
                        body: "The application has been successfully released to production.\n\nBuild: ${BUILD_NUMBER}\nCommit: ${GIT_COMMIT_SHORT}\nProduction URLs:\n- Product Service: ${PROD_PRODUCT_SERVICE_URL}\n- Order Service: ${PROD_ORDER_SERVICE_URL}\n- Frontend: ${PROD_FRONTEND_URL}",
                        to: "dev-team@company.com,ops-team@company.com"
                    )
                }
                failure {
                    echo 'Production release failed!'
                    emailext (
                        subject: "CRITICAL: Production Release Failed - Build ${BUILD_NUMBER}",
                        body: "The production release has failed. Immediate attention required!\n\nBuild: ${BUILD_NUMBER}\nCommit: ${GIT_COMMIT_SHORT}",
                        to: "dev-team@company.com,ops-team@company.com,management@company.com"
                    )
                }
            }
        }
        
        stage('Monitoring and Alerting') {
            steps {
                echo 'Setting up monitoring and alerting...'
                script {
                    // Configure Prometheus monitoring
                    sh '''
                        # Update Prometheus configuration
                        cat > prometheus/prometheus.yml << EOF
                        global:
                          scrape_interval: 15s
                          evaluation_interval: 15s

                        rule_files:
                          - "alert_rules.yml"

                        alerting:
                          alertmanagers:
                            - static_configs:
                                - targets:
                                  - alertmanager:9093

                        scrape_configs:
                          - job_name: 'product-service'
                            static_configs:
                              - targets: ['product-service:8000']
                            metrics_path: '/metrics'
                            scrape_interval: 5s
                            
                          - job_name: 'order-service'
                            static_configs:
                              - targets: ['order-service:8000']
                            metrics_path: '/metrics'
                            scrape_interval: 5s
                            
                          - job_name: 'postgres'
                            static_configs:
                              - targets: ['postgres-exporter:9187']
                            
                          - job_name: 'node-exporter'
                            static_configs:
                              - targets: ['node-exporter:9100']
                        EOF
                        
                        # Start monitoring stack
                        docker-compose -f docker-compose.monitoring.yml up -d
                        
                        # Wait for monitoring to be ready
                        sleep 30
                        
                        # Verify monitoring is working
                        curl -f http://localhost:9090/api/v1/targets || echo "Prometheus not ready yet"
                        curl -f http://localhost:3000/api/health || echo "Grafana not ready yet"
                    '''
                }
            }
            post {
                success {
                    echo 'Monitoring setup completed!'
                    emailext (
                        subject: "Monitoring Setup Complete - Build ${BUILD_NUMBER}",
                        body: "Monitoring and alerting have been configured for the application.\n\nBuild: ${BUILD_NUMBER}\nMonitoring URLs:\n- Prometheus: http://monitoring-server:9090\n- Grafana: http://monitoring-server:3000\n- AlertManager: http://monitoring-server:9093",
                        to: "ops-team@company.com"
                    )
                }
            }
        }
    }
    
    post {
        always {
            echo 'Pipeline execution completed!'
            // Clean up workspace
            cleanWs()
        }
        success {
            echo 'Pipeline executed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
            // Send failure notification
            emailext (
                subject: "Pipeline Failed - Build ${BUILD_NUMBER}",
                body: "The Jenkins pipeline has failed. Please check the logs for details.\n\nBuild: ${BUILD_NUMBER}\nCommit: ${GIT_COMMIT_SHORT}\nPipeline URL: ${BUILD_URL}",
                to: "dev-team@company.com"
            )
        }
        unstable {
            echo 'Pipeline completed with warnings!'
        }
    }
}
