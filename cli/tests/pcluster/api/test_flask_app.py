#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at http://aws.amazon.com/apache2.0/
#  or in the "LICENSE.txt" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and
#  limitations under the License.
import logging

import pytest
from assertpy import assert_that
from connexion.exceptions import BadRequestProblem
from werkzeug.exceptions import InternalServerError, MethodNotAllowed

from pcluster.api.errors import BadRequestException, InternalServiceException
from pcluster.api.flask_app import ParallelClusterFlaskApp
from pcluster.api.models import InternalServiceExceptionResponseContent


class TestParallelClusterFlaskApp:
    @pytest.fixture(autouse=True)
    def configure_caplog(self, caplog):
        caplog.set_level(logging.INFO, logger="pcluster")

    @staticmethod
    def _assert_response(response, body, code, mimetype="application/json"):
        assert_that(response.get_data().decode()).is_equal_to(body)
        assert_that(response.status_code).is_equal_to(code)
        assert_that(response.mimetype).is_equal_to(mimetype)

    @staticmethod
    def _assert_log_message(caplog, level, message):
        assert_that(caplog.records).is_length(1)
        assert_that(caplog.records[0].levelno).is_equal_to(level)
        assert_that(caplog.records[0].message).contains(message)
        if level >= logging.ERROR:
            assert_that(caplog.records[0].exc_info).is_true()
        else:
            assert_that(caplog.records[0].exc_info).is_false()

    def test_handle_http_exception(self, caplog):
        response = ParallelClusterFlaskApp._handle_http_exception(MethodNotAllowed())

        self._assert_response(
            response, body='{"message": "The method is not allowed for the requested URL."}', code=405
        )
        self._assert_log_message(
            caplog,
            logging.INFO,
            "Handling exception (status code 405): The method is not allowed for the requested URL.",
        )

        caplog.clear()
        response = ParallelClusterFlaskApp._handle_http_exception(InternalServerError())

        self._assert_response(
            response,
            body='{"message": "The server encountered an internal error and was unable to complete your request. '
            'Either the server is overloaded or there is an error in the application."}',
            code=500,
        )
        self._assert_log_message(
            caplog, logging.ERROR, "Handling exception (status code 500): The server encountered an internal error"
        )

    def test_handle_parallel_cluster_api_exception(self, caplog):
        response = ParallelClusterFlaskApp._handle_parallel_cluster_api_exception(
            BadRequestException("invalid request")
        )

        self._assert_response(response, body='{"message": "Bad Request: invalid request"}', code=400)
        self._assert_log_message(
            caplog,
            logging.INFO,
            "Handling exception (status code 400): {'message': 'Bad Request: invalid request'}",
        )

        caplog.clear()
        response = ParallelClusterFlaskApp._handle_parallel_cluster_api_exception(
            InternalServiceException(InternalServiceExceptionResponseContent("failure"))
        )

        self._assert_response(
            response,
            body='{"message": "failure"}',
            code=500,
        )
        self._assert_log_message(caplog, logging.ERROR, "Handling exception (status code 500): {'message': 'failure'}")

    def test_handle_unexpected_exception(self, caplog):
        response = ParallelClusterFlaskApp._handle_unexpected_exception(Exception("error"))

        self._assert_response(
            response,
            body='{"message": "Unexpected fatal exception. '
            'Please look at the application logs for details on the encountered failure."}',
            code=500,
        )
        self._assert_log_message(
            caplog,
            logging.CRITICAL,
            "Unexpected exception: error",
        )

    def test_handle_problem_exception(self, caplog):
        response = ParallelClusterFlaskApp._handle_problem_exception(BadRequestProblem(detail="malformed"))
        self._assert_response(response, body='{"message": "Bad Request: malformed"}', code=400)
        self._assert_log_message(
            caplog,
            logging.INFO,
            "Handling exception (status code 400): Bad Request: malformed",
        )