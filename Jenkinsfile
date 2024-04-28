import groovy.json.JsonSlurper
import hudson.FilePath
import java.text.SimpleDateFormat

//WORK_NODE=master
//NODE_ENV=development
//PROJECT_NAME=project_name
//PROJECT_FULL_NAME=Project Name
//EXPOSE_PORT=8000
//SLACK_CHANNEL=#channel
//EMAIL_RECEIVER=dev@example.com;cc:dev-cc@example.com
//LOGO_URL=https://api.slack.com/img/blocks/bkb_template_images/approvalsNewDevice.png

pipeline {
    agent {
        node {
            label "${WORK_NODE}"
        }
    }
    options {
        timeout(time: 30, unit: "MINUTES")
    }
    stages {
        stage("Check Runtime Image") {
            steps {
                buildName "Binary Owl Backend ${NODE_ENV.capitalize()} Auto Deploy NO.${BUILD_NUMBER}"
                buildDescription "Build On Node: ${NODE_NAME} By ${BUILD_USER}"

                script {
                    sh """
                        sudo sed -i "s/PROJECT_NAME/${PROJECT_NAME}/g" Dockerfile
                        cat Dockerfile
                        sudo sed -i "s/PROJECT_NAME/${PROJECT_NAME}-${NODE_ENV}/g" docker-compose.yaml
                        sudo sed -i "s/EXPOSE_PORT/${EXPOSE_PORT}/g" docker-compose.yaml
                        cat docker-compose.yaml
                    """

                    def projectRuntimeDockerImageExists = !sh(returnStatus: true, script: "sudo docker inspect ${PROJECT_NAME}-runtime:latest")
                    println "Project Runtime Docker Image Exists: ${projectRuntimeDockerImageExists}"

                    env.GIT_CHANGE_FILE_LIST = sh(returnStdout: true, script: 'sudo git diff --name-only HEAD~1').trim().replaceAll("\\n", " ")
                    println "Change File List Of Nearest Commit: ${GIT_CHANGE_FILE_LIST}"

                    def runtimeDockerfileChanged = env.GIT_CHANGE_FILE_LIST.matches(/.*RuntimeDockerfile.*/)
                    println "Need rebuild Runtime Docker Image: ${runtimeDockerfileChanged}"

                    def nodeRequireModulesChanged = env.GIT_CHANGE_FILE_LIST.matches(/.*Pipfile.*/)
                    println "has Node Require Modules been changed: ${nodeRequireModulesChanged}"

                    if (projectRuntimeDockerImageExists) {
                        if (runtimeDockerfileChanged || nodeRequireModulesChanged) {
                            sh "sudo docker rmi -f ${PROJECT_NAME}-runtime:latest"
                            sh "sudo docker build -f ./RuntimeDockerfile -t ${PROJECT_NAME}-runtime:latest ."
                        }
                    } else {
                        sh "sudo docker build -f ./RuntimeDockerfile -t ${PROJECT_NAME}-runtime:latest ."
                    }
                }
            }
        }
        stage("Build Image") {
            steps {
                script {
                    sh "sudo cp -f /mnt/data/runtime-env/${PROJECT_NAME}-${NODE_ENV}-env ./.env"

                    def projectDockerImageExists = !sh(returnStatus: true, script: "sudo docker inspect ${PROJECT_NAME}-${NODE_ENV}:latest")
                    println "Project Docker Image Exists: ${projectDockerImageExists}"

                    def projectDockerContainerExists = !sh(returnStatus: true, script: "sudo docker inspect ${PROJECT_NAME}-${NODE_ENV}")
                    println "Project Docker Container Exists: ${projectDockerContainerExists}"

                    if (projectDockerImageExists) {
                        if (projectDockerContainerExists) {
                            sh "sudo docker-compose down"
                        }
                        sh "sudo docker rmi -f ${PROJECT_NAME}-${NODE_ENV}:latest"
                    }
                    sh "sudo docker build -t ${PROJECT_NAME}-${NODE_ENV}:latest ."
                }
            }
        }
        stage("Deploy") {
            steps {
                script {
                    sh "sudo docker-compose up -d"
                }
            }
        }
    }
    post {
        always {
            slackSend channel: "$SLACK_CHANNEL", blocks: genSlackNotificationBlocks(currentBuild)
            emailext subject: "[Auto Deploy] - $PROJECT_FULL_NAME ${NODE_ENV.capitalize()} Build Result",
                body: '''${SCRIPT, template="managed:Groovy Email Build Result Template"}''',
                to: '${DEFAULT_RECIPIENTS}; $EMAIL_RECEIVER',
                mimeType: "text/html"
        }
    }
}

def genSlackNotificationBlocks(build) {
    def resultIconMap = [
        'SUCCESS': ':large_green_circle:',
        'FAILURE': ':red_circle:',
        'UNSTABLE': ':large_orange_circle:',
    ]
    def changeSets = build.changeSets
    def changeDetail = new StringBuilder()
    if (changeSets != null) {
        def hadChanges = false
        changeSets.each { cs_list ->
            cs_list.each { cs ->
                hadChanges = true
                changeDetail.append("*Changes:*\n")
                def match = cs.msgAnnotated =~ /<a href='(.*?)'/
                def commitDetail = new StringBuilder()
                if (match) {
                    def commitIDMatch = cs.msgAnnotated =~ />(commit.*)</
                    def result = "<${match[0][1]}|${commitIDMatch[0][1]}>"
                    commitDetail.append(cs.msgAnnotated.replaceAll(/<a.*<\/a>/, result))
                }
                changeDetail.append("\tRevision by ${cs.author}${commitDetail ? ':' : ''}\t${commitDetail}\n")
                cs.affectedFiles.each { p ->
                    changeDetail.append("\t${p.editType.name}:\t\t${p.path}\n")
                }
            }
        }
        if (!hadChanges) {
            changeDetail.append("\tNo Changes")
        }
        println(changeDetail.toString())
    }


    return [[
        "type": "header",
        "text": [
            "type": "plain_text",
            "text": "Jenkins Auto Deploy Job Build Result",
            "emoji": true
        ]
    ], [
        "type": "section",
        "text": [
            "type": "mrkdwn",
            "text": "${resultIconMap[build.result]} *<${BUILD_URL}|Binary Owl Backend ${NODE_ENV.capitalize()}>*\t<@U05H9MAFMBM> <@U036EQRRFU7> <@U01G2KHDKKK>"
        ]
    ], [
        "type": "section",
        "text": [
            "type": "mrkdwn",
            "text": "*Cause:*\n\t${build.getBuildCauses().collect { it.shortDescription }.join(" ")}\n*Date:*\n\t${new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(build.getTimeInMillis())}\n*Duration:*\n\t${build.durationString}"
        ],
        "accessory": [
            "type": "image",
            "image_url": "${LOGO_URL}",
            "alt_text": "project link"
        ]
    ], [
        "type": "section",
        "text": [
            "type": "mrkdwn",
            "text": changeDetail
        ]
    ], [
        "type": "actions",
        "elements": [[
            "type": "button",
            "text": [
                "type": "plain_text",
                "emoji": true,
                "text": "Click To View Build Logs"
            ],
            "style": "primary",
            "url": "${BUILD_URL}/console"
        ]]
    ], [
        "type": "divider"
    ]]
}
