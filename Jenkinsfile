@Library('jenkins-library')

List   jobParams             = [
    string(defaultValue: 'sora', name: 'networkname', trim: true),
    string(defaultValue: "cnUZkAbtX2u9ko8g6uwihfGNUrXTVEiG2oB4ZTU5VF98eqe43", name: 'address', trim: true),
    string(defaultValue: '11642981', name: 'fromblock', trim: true),
    string(defaultValue: '11642983', name: 'toblock', trim: true),
]
String registry               = 'docker.soramitsu.co.jp'
String dockerBuildToolsUserId = 'bot-build-tools-ro'
String agentLabel             = 'docker-build-agent'
String agentImage             = registry + '/build-tools/python:3.11'
String telegramChatIdReports    = 'telegramChatIdReports'
String telegramBotToken       = 'telegramBotToken'
String secretScannerExclusion = '.*template_config.json\$'
Boolean disableSecretScanner  = false

properties([
    parameters( jobParams ),
])

pipeline {
    options {
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
        disableConcurrentBuilds()
    }
    agent {
        label agentLabel
    }
    stages {
        stage('Reporting') {
            environment {
                TELEGRAM_CHAT_ID = credentials("${telegramChatIdReports}")
                TELEGRAM_BOT_TOKEN = credentials("${telegramBotToken}")
            }
            steps {
                script {
                    docker.withRegistry( 'https://' + registry, dockerBuildToolsUserId) {
                        docker.image( agentImage ).inside() {
                            sh """
                                export networkname="${networkname}"
                                export address="${address}"
                                export fromblock="${fromblock}"
                                export toblock="${toblock}"
                                ./housekeeping/sendreport.sh
                            """
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            script{gitNotify('main-CI', currentBuild.result, currentBuild.result)}
        }
        cleanup { cleanWs() }
    }
}