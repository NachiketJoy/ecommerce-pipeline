pipeline {
    agent any
    
    environment {
        // Docker and Registry Configuration
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_NAMESPACE = 'njoy10'
        
        // Application Configuration
    PRODUCT_SERVICE_IMAGE = "product-service"
    ORDER_SERVICE_IMAGE = "order-service"
    FRONTEND_IMAGE = "frontend"
        
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
                    env.GIT_COMMIT_SHORT = bat(
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
                                bat '''
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
                                bat '''
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
                            bat '''
                                docker-compose -f docker-compose.test.yml up -d
                                timeout /t 30 /nobreak >nul 2>&1
                            '''
                            
                            // Run integration tests
                            bat '''
                                docker run --rm --network ecommerce_test_network ^
                                    -e PRODUCT_SERVICE_URL=http://product-service-test:8000 ^
                                    -e ORDER_SERVICE_URL=http://order-service-test:8000 ^
                                    %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG% ^
                                    python -m pytest tests/integration/ -v --junitxml=integration-test-results.xml
                            '''
                        }
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: '**/integration-test-results.xml'
                            bat 'docker-compose -f docker-compose.test.yml down -v'
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
                                bat '''
                                    cd /app
                                    sonar-scanner ^
                                        -Dsonar.projectKey=ecommerce-product-service ^
                                        -Dsonar.sources=. ^
                                        -Dsonar.host.url=%SONAR_HOST_URL% ^
                                        -Dsonar.login=%SONAR_TOKEN% ^
                                        -Dsonar.python.coverage.reportPaths=coverage.xml ^
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
                                bat '''
                                    cd /app
                                    sonar-scanner ^
                                        -Dsonar.projectKey=ecommerce-order-service ^
                                        -Dsonar.sources=. ^
                                        -Dsonar.host.url=%SONAR_HOST_URL% ^
                                        -Dsonar.login=%SONAR_TOKEN% ^
                                        -Dsonar.python.coverage.reportPaths=coverage.xml ^
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
                            bat '''
                                @echo off
                                REM Install Trivy if not present
                                where trivy >nul 2>&1
                                if %errorlevel% neq 0 (
                                    echo Installing Trivy...
                                    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/aquasecurity/trivy/releases/latest/download/trivy_windows_amd64.zip' -OutFile 'trivy.zip'"
                                    powershell -Command "Expand-Archive -Path 'trivy.zip' -DestinationPath '.' -Force"
                                    move trivy.exe C:\\Windows\\System32\\
                                    del trivy.zip
                                )
                                
                                REM Scan all images
                                trivy image --format json --output trivy-report.json %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG%
                                trivy image --format json --output trivy-report-order.json %ORDER_SERVICE_IMAGE%:%BUILD_TAG%
                                trivy image --format json --output trivy-report-frontend.json %FRONTEND_IMAGE%:%BUILD_TAG%
                                
                                REM Generate HTML reports
                                trivy image --format template --template "@contrib/html.tpl" --output trivy-report.html %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG%
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
                                bat '''
                                    cd /app
                                    REM Install bandit
                                    pip install bandit
                                    
                                    REM Run bandit scan
                                    bandit -r . -f json -o bandit-report.json
                                    bandit -r . -f html -o bandit-report.html
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
                    bat '''
                        docker tag %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:test
                        docker tag %ORDER_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:test
                        docker tag %FRONTEND_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:test
                    '''
                    
                    // Deploy to test environment
                    bat '''
                        REM Update docker-compose.test.yml with new image tags
                        powershell -Command "(Get-Content docker-compose.test.yml) -replace 'image: .*product-service.*', 'image: %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:test' | Set-Content docker-compose.test.yml"
                        powershell -Command "(Get-Content docker-compose.test.yml) -replace 'image: .*order-service.*', 'image: %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:test' | Set-Content docker-compose.test.yml"
                        powershell -Command "(Get-Content docker-compose.test.yml) -replace 'image: .*frontend.*', 'image: %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:test' | Set-Content docker-compose.test.yml"
                        
                        REM Deploy to test environment
                        docker-compose -f docker-compose.test.yml up -d
                        
                        REM Wait for services to be healthy
                        timeout /t 30 /nobreak >nul 2>&1
                        
                        REM Run health checks
                        curl -f http://localhost:8000/health
                        curl -f http://localhost:8001/health
                        curl -f http://localhost:3000/
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
                    bat '''
                        docker tag %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:latest
                        docker tag %PRODUCT_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:%BUILD_TAG%
                        docker tag %ORDER_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:latest
                        docker tag %ORDER_SERVICE_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:%BUILD_TAG%
                        docker tag %FRONTEND_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:latest
                        docker tag %FRONTEND_IMAGE%:%BUILD_TAG% %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:%BUILD_TAG%
                    '''
                    
                    // Push to registry
                    bat '''
                        docker push %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:latest
                        docker push %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:%BUILD_TAG%
                        docker push %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:latest
                        docker push %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:%BUILD_TAG%
                        docker push %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:latest
                        docker push %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:%BUILD_TAG%
                    '''
                    
                    // Deploy to production
                    bat '''
                        REM Update production docker-compose
                        powershell -Command "(Get-Content docker-compose.prod.yml) -replace 'image: .*product-service.*', 'image: %DOCKER_NAMESPACE%/%PRODUCT_SERVICE_IMAGE%:latest' | Set-Content docker-compose.prod.yml"
                        powershell -Command "(Get-Content docker-compose.prod.yml) -replace 'image: .*order-service.*', 'image: %DOCKER_NAMESPACE%/%ORDER_SERVICE_IMAGE%:latest' | Set-Content docker-compose.prod.yml"
                        powershell -Command "(Get-Content docker-compose.prod.yml) -replace 'image: .*frontend.*', 'image: %DOCKER_NAMESPACE%/%FRONTEND_IMAGE%:latest' | Set-Content docker-compose.prod.yml"
                        
                        REM Deploy to production
                        docker-compose -f docker-compose.prod.yml up -d
                        
                        REM Wait for services to be healthy
                        timeout /t 60 /nobreak >nul 2>&1
                        
                        REM Run production health checks
                        curl -f http://localhost:8000/health
                        curl -f http://localhost:8001/health
                        curl -f http://localhost:3000/
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
                    bat '''
                        REM Update Prometheus configuration
                        echo global: > prometheus\\prometheus.yml
                        echo   scrape_interval: 15s >> prometheus\\prometheus.yml
                        echo   evaluation_interval: 15s >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo rule_files: >> prometheus\\prometheus.yml
                        echo   - "alert_rules.yml" >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo alerting: >> prometheus\\prometheus.yml
                        echo   alertmanagers: >> prometheus\\prometheus.yml
                        echo     - static_configs: >> prometheus\\prometheus.yml
                        echo         - targets: >> prometheus\\prometheus.yml
                        echo           - alertmanager:9093 >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo scrape_configs: >> prometheus\\prometheus.yml
                        echo   - job_name: 'product-service' >> prometheus\\prometheus.yml
                        echo     static_configs: >> prometheus\\prometheus.yml
                        echo       - targets: ['product-service:8000'] >> prometheus\\prometheus.yml
                        echo     metrics_path: '/metrics' >> prometheus\\prometheus.yml
                        echo     scrape_interval: 5s >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo   - job_name: 'order-service' >> prometheus\\prometheus.yml
                        echo     static_configs: >> prometheus\\prometheus.yml
                        echo       - targets: ['order-service:8000'] >> prometheus\\prometheus.yml
                        echo     metrics_path: '/metrics' >> prometheus\\prometheus.yml
                        echo     scrape_interval: 5s >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo   - job_name: 'postgres' >> prometheus\\prometheus.yml
                        echo     static_configs: >> prometheus\\prometheus.yml
                        echo       - targets: ['postgres-exporter:9187'] >> prometheus\\prometheus.yml
                        echo. >> prometheus\\prometheus.yml
                        echo   - job_name: 'node-exporter' >> prometheus\\prometheus.yml
                        echo     static_configs: >> prometheus\\prometheus.yml
                        echo       - targets: ['node-exporter:9100'] >> prometheus\\prometheus.yml
                        
                        REM Start monitoring stack
                        docker-compose -f docker-compose.monitoring.yml up -d
                        
                        REM Wait for monitoring to be ready
                        timeout /t 30 /nobreak >nul 2>&1
                        
                        REM Verify monitoring is working
                        curl -f http://localhost:9090/api/v1/targets
                        curl -f http://localhost:3000/api/health
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
