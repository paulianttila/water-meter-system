#!/usr/bin/env bash

TAVERN_LOG_LEVEL=INFO

# exit when any command fails
set -e

trap "clean_up" EXIT

PWD=$(pwd)

# set configuration for test app
export LOG_LEVEL=DEBUG
export ROOT_DIR=${PWD}/src
export CONFIG_DIR=${PWD}/test_config
export IMAGE_TMP=${PWD}/image_tmp

TEST_APP_PID=

start_test_app() {
  # start the test app whch use framework
  echo "Start test app"
  cd src
  python meter.py &
  sleep 2
  TEST_APP_PID=$!
  echo "PID=${TEST_APP_PID}"
  jobs
  cd ..
}

run_tests() {
  # add testing_utils.py to tavern tests
  export PYTHONPATH=${PYTHONPATH}:${PWD}/tests/integration/

  # run tests
  python -m pytest --log-cli-level=${TAVERN_LOG_LEVEL} tests/
}

clean_up() {
  echo "Stop test app, PID=${TEST_APP_PID}"
  kill -9 ${TEST_APP_PID}
}

echo "Current folder: ${PWD}"

start_test_app
run_tests