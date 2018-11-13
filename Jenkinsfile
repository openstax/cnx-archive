@Library('pipeline-library') _

pipeline {
  agent { label 'docker' }
  environment {
    TESTING_CONTAINER_NAME = "archive-testing-${env.BUILD_ID}"
  }
  stages {
    stage('Build') {
      steps {
        sh "docker build -t openstax/cnx-archive:dev ."
      }
    }
    stage('Publish Dev Container') {
      steps {
        // 'docker-registry' is defined in Jenkins under credentials
        withDockerRegistry([credentialsId: 'docker-registry', url: '']) {
          sh "docker push openstax/cnx-archive:dev"
        }
      }
    }
    stage('Deploy to the Staging stack') {
      when { branch 'master' }
      steps {
        // Requires DOCKER_HOST be set in the Jenkins Configuration.
        // Using the environment variable enables this file to be
        // endpoint agnostic.
        sh "docker -H ${CNX_STAGING_DOCKER_HOST} service update --label-add 'git.commit-hash=${GIT_COMMIT}' --image openstax/cnx-archive:dev staging_archive"
      }
    }
    stage('Run Functional Tests'){
      when { branch 'master' }
      steps {
          runCnxFunctionalTests(testingDomain: "${env.CNX_STAGING_DOCKER_HOST}")
      }
    }
    stage('Publish Release') {
      when { buildingTag() }
      environment {
        TWINE_CREDS = credentials('pypi-openstax-creds')
        TWINE_USERNAME = "${TWINE_CREDS_USR}"
        TWINE_PASSWORD = "${TWINE_CREDS_PSW}"
        release = meta.version()
      }
      steps {
        withDockerRegistry([credentialsId: 'docker-registry', url: '']) {
          sh "docker tag openstax/cnx-archive:dev openstax/cnx-archive:${release}"
          sh "docker tag openstax/cnx-archive:dev openstax/cnx-archive:latest"
          sh "docker push openstax/cnx-archive:${release}"
          sh "docker push openstax/cnx-archive:latest"
        }
        // Note, '.git' is a volume, because versioneer needs it to resolve the python distribution's version. 
        sh "docker run --rm -e TWINE_USERNAME -e TWINE_PASSWORD -v ${WORKSPACE}/.git:/src/.git:ro openstax/cnx-archive:latest /bin/bash -c \"pip install -q twine && python2 setup.py bdist_wheel && twine upload dist/*\""
      }
    }
  }
}
